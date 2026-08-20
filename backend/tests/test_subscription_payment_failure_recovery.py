"""
Verifica due lacune nella gestione dei pagamenti ricorrenti, trovate
rileggendo subscription_service.py: prima di questo fix, un rinnovo Stripe
fallito era invisibile all'app (nessun evento gestito lo segnalava, quindi
l'utente restava con subscription_status="active" mentre l'incasso non
arrivava), e un cliente PayPal che pagava con successo dopo un primo
addebito fallito restava bloccato (subscription_status="payment_failed" non
veniva mai riportato ad "active" da nessun evento).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_subscription_payment_failure_recovery.py -v
"""
import sys
import asyncio

import pytest

sys.path.insert(0, ".")

import services.subscription_service as subscription_mod
from services.subscription_service import SubscriptionService
from tests.test_subscription_cancel_grace_period import (
    FakeUserRepo, FakeWebhookEventsCollection, FakeRequest,
)


def run(coro):
    return asyncio.run(coro)


class TrackingFakeUserRepo(FakeUserRepo):
    """FakeUserRepo di test_subscription_cancel_grace_period non traccia le
    chiamate a update_by_stripe_subscription_id/update_by_paypal_subscription_id
    in self.updates (solo update_by_id lo fa) — qui serve invece poter
    verificare con certezza che NESSUNA scrittura sia avvenuta, non solo
    dedurlo dal valore finale invariato."""

    async def update_by_stripe_subscription_id(self, sub_id, data):
        self.updates.append((sub_id, data))
        await super().update_by_stripe_subscription_id(sub_id, data)

    async def update_by_paypal_subscription_id(self, sub_id, data):
        self.updates.append((sub_id, data))
        await super().update_by_paypal_subscription_id(sub_id, data)


# ---------- Webhook Stripe: customer.subscription.updated ----------

def _stripe_updated_event(sub_id: str, status: str) -> dict:
    return {
        "id": f"evt-{sub_id}-{status}",
        "type": "customer.subscription.updated",
        "data": {"object": {"id": sub_id, "status": status}},
    }


def _install_fake_stripe_webhook(monkeypatch, event: dict):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(subscription_mod, "stripe_webhook_events", FakeWebhookEventsCollection())

    class FakeWebhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            return event

    fake_stripe_module = type("FakeStripe", (), {"api_key": None, "Webhook": FakeWebhook})
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)


def test_webhook_stripe_rinnovo_fallito_passa_a_past_due(monkeypatch):
    """Il caso centrale del fix: prima non esisteva nessun ramo per questo
    evento, quindi lo status restava 'active' mentre Stripe segnalava un
    rinnovo fallito — l'app non aveva modo di saperlo."""
    event = _stripe_updated_event("sub_1", "past_due")
    _install_fake_stripe_webhook(monkeypatch, event)

    repo = FakeUserRepo({"user-1": {
        "id": "user-1", "stripe_subscription_id": "sub_1", "subscription_status": "active",
    }})
    service = SubscriptionService(repo=repo)

    result = run(service.handle_stripe_webhook(FakeRequest(headers={"stripe-signature": "sig"})))

    assert result == {"ok": True}
    assert repo.users_by_id["user-1"]["subscription_status"] == "past_due"


def test_webhook_stripe_rinnovo_fallito_blocca_davvero_laccesso(monkeypatch):
    """Non basta che lo stato cambi: deve anche tradursi in accesso
    bloccato, tramite is_subscription_active (nessuna modifica necessaria
    lì: qualunque status diverso da 'active'/'trial' è già trattato come
    non attivo)."""
    from core.subscription_utils import is_subscription_active
    assert is_subscription_active({"subscription_status": "past_due"}) is False


def test_webhook_stripe_rinnovo_recuperato_torna_active(monkeypatch):
    """Un tentativo di recupero riuscito (Stripe Smart Retries) fa tornare
    l'evento con status 'active': l'accesso deve ripristinarsi da solo,
    senza intervento manuale."""
    event = _stripe_updated_event("sub_2", "active")
    _install_fake_stripe_webhook(monkeypatch, event)

    repo = FakeUserRepo({"user-2": {
        "id": "user-2", "stripe_subscription_id": "sub_2", "subscription_status": "past_due",
    }})
    service = SubscriptionService(repo=repo)

    run(service.handle_stripe_webhook(FakeRequest(headers={"stripe-signature": "sig"})))

    assert repo.users_by_id["user-2"]["subscription_status"] == "active"


def test_webhook_stripe_updated_canceled_mappa_su_cancelled(monkeypatch):
    """Stripe usa 'canceled' (inglese americano); il resto del codice usa
    sempre 'cancelled' (vedi cancel_subscription/handle_stripe_webhook per
    customer.subscription.deleted) — deve restare coerente anche qui."""
    event = _stripe_updated_event("sub_3", "canceled")
    _install_fake_stripe_webhook(monkeypatch, event)

    repo = FakeUserRepo({"user-3": {
        "id": "user-3", "stripe_subscription_id": "sub_3", "subscription_status": "past_due",
    }})
    service = SubscriptionService(repo=repo)

    run(service.handle_stripe_webhook(FakeRequest(headers={"stripe-signature": "sig"})))

    assert repo.users_by_id["user-3"]["subscription_status"] == "cancelled"


def test_webhook_stripe_updated_senza_status_non_scrive_nulla(monkeypatch):
    event = {
        "id": "evt-no-status", "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_4"}},
    }
    _install_fake_stripe_webhook(monkeypatch, event)

    repo = TrackingFakeUserRepo({"user-4": {
        "id": "user-4", "stripe_subscription_id": "sub_4", "subscription_status": "active",
    }})
    service = SubscriptionService(repo=repo)

    run(service.handle_stripe_webhook(FakeRequest(headers={"stripe-signature": "sig"})))

    assert repo.users_by_id["user-4"]["subscription_status"] == "active"
    assert repo.updates == []


# ---------- Webhook PayPal: recupero da payment_failed ----------

def _paypal_event(event_type: str, sub_id: str, event_id: str = "evt-p1") -> dict:
    return {"id": event_id, "event_type": event_type, "resource": {"id": sub_id}}


def test_webhook_paypal_pagamento_riuscito_dopo_fallito_riattiva(monkeypatch):
    """Il caso centrale del fix: prima PAYMENT.SALE.COMPLETED non faceva
    nulla, quindi un cliente rimasto 'payment_failed' restava bloccato
    anche dopo aver pagato con successo al tentativo successivo."""
    monkeypatch.setattr(subscription_mod, "paypal_webhook_events", FakeWebhookEventsCollection())

    repo = FakeUserRepo({"user-5": {
        "id": "user-5", "paypal_subscription_id": "I-FAIL-THEN-OK", "subscription_status": "payment_failed",
    }})
    service = SubscriptionService(repo=repo)
    monkeypatch.setattr(service, "_verify_paypal_webhook_signature", lambda *a, **k: True)

    event = _paypal_event("PAYMENT.SALE.COMPLETED", "I-FAIL-THEN-OK")
    result = run(service.handle_paypal_webhook(FakeRequest(json_data=event)))

    assert result == {"ok": True}
    assert repo.users_by_id["user-5"]["subscription_status"] == "active"


def test_webhook_paypal_pagamento_riuscito_su_abbonamento_gia_attivo_non_lo_tocca(monkeypatch):
    """Un PAYMENT.SALE.COMPLETED su un abbonamento già attivo (il normale
    rinnovo mensile che va a buon fine) non deve scrivere nulla di
    inutile: il ramo si attiva solo per un vero recupero da payment_failed."""
    monkeypatch.setattr(subscription_mod, "paypal_webhook_events", FakeWebhookEventsCollection())

    repo = TrackingFakeUserRepo({"user-6": {
        "id": "user-6", "paypal_subscription_id": "I-ALREADY-ACTIVE", "subscription_status": "active",
    }})
    service = SubscriptionService(repo=repo)
    monkeypatch.setattr(service, "_verify_paypal_webhook_signature", lambda *a, **k: True)

    event = _paypal_event("PAYMENT.SALE.COMPLETED", "I-ALREADY-ACTIVE")
    run(service.handle_paypal_webhook(FakeRequest(json_data=event)))

    assert repo.updates == []
    assert repo.users_by_id["user-6"]["subscription_status"] == "active"


def test_webhook_paypal_pagamento_riuscito_su_sospeso_non_lo_riattiva(monkeypatch):
    """Un evento di pagamento riuscito non deve riattivare un abbonamento
    sospeso o cancellato per altri motivi — solo il caso specifico
    payment_failed -> active è un vero recupero."""
    monkeypatch.setattr(subscription_mod, "paypal_webhook_events", FakeWebhookEventsCollection())

    repo = TrackingFakeUserRepo({"user-7": {
        "id": "user-7", "paypal_subscription_id": "I-SUSPENDED", "subscription_status": "suspended",
    }})
    service = SubscriptionService(repo=repo)
    monkeypatch.setattr(service, "_verify_paypal_webhook_signature", lambda *a, **k: True)

    event = _paypal_event("PAYMENT.SALE.COMPLETED", "I-SUSPENDED")
    run(service.handle_paypal_webhook(FakeRequest(json_data=event)))

    assert repo.updates == []
    assert repo.users_by_id["user-7"]["subscription_status"] == "suspended"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
