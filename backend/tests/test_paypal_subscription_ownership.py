"""
Verifica il fix del dirottamento di un abbonamento PayPal altrui:
paypal_capture() ora verifica che il subscription_id inviato dal
frontend sia davvero quello che QUESTO account si aspettava
(pending_paypal_subscription_id, impostato da create_paypal_subscription)
o quello già legato ad esso in precedenza — non un id arbitrario che
PayPal confermerebbe comunque come reale/attivo indipendentemente da
chi lo sta presentando.

Prima di questo fix, chiunque conoscesse il subscription_id reale e
ACTIVE di un altro utente (es. trapelato via email di conferma, log,
screenshot) poteva inviarlo come proprio a POST
/api/subscription/paypal-capture e ottenere accesso a pagamento
gratuito legato all'abbonamento (già pagato) della vittima.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_paypal_subscription_ownership.py -v
"""
import sys
import asyncio

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

import services.subscription_service as subscription_mod
from services.subscription_service import SubscriptionService
from tests.test_subscription_cancel_grace_period import FakeUserRepo, FakeResponse


def run(coro):
    return asyncio.run(coro)


class FakeRequestsPayPalCapture:
    """Sostituisce il modulo `requests` per l'intero flusso
    create_paypal_subscription -> paypal_capture: gestisce sia la
    creazione dell'abbonamento (POST .../subscriptions) sia la lettura
    del suo stato reale (GET .../subscriptions/{id})."""

    def __init__(self, real_subscription_id="I-REAL123", status="ACTIVE", plan_id="P-FAKE"):
        self.real_subscription_id = real_subscription_id
        self.status = status
        self.plan_id = plan_id
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url))
        if "/oauth2/token" in url:
            return FakeResponse(200, {"access_token": "fake-token"})
        if url.endswith("/v1/billing/subscriptions"):
            return FakeResponse(201, {
                "id": self.real_subscription_id,
                "links": [{"rel": "approve", "href": "https://paypal.example/approve"}],
            })
        return FakeResponse(200, {})

    def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        return FakeResponse(200, {
            "status": self.status,
            "plan_id": self.plan_id,
            "billing_info": {"next_billing_time": "2026-09-01T00:00:00Z"},
        })


def build_service(fake_requests):
    monkeypatch_targets = []
    repo = FakeUserRepo({})
    service = SubscriptionService(repo=repo)
    return service, repo


PLAN_FAKE = {"base": {"paypal_plan_id": "P-FAKE"}}


def test_create_paypal_subscription_registra_id_atteso(monkeypatch):
    fake_requests = FakeRequestsPayPalCapture()
    monkeypatch.setattr(subscription_mod, "requests", fake_requests)
    monkeypatch.setattr(subscription_mod, "PLANS", PLAN_FAKE)

    repo = FakeUserRepo({"user-1": {"id": "user-1", "is_demo": False}})
    service = SubscriptionService(repo=repo)

    result = run(service.create_paypal_subscription({"id": "user-1"}, {"plan": "base"}))

    assert result["subscription_id"] == "I-REAL123"
    assert repo.users_by_id["user-1"]["pending_paypal_subscription_id"] == "I-REAL123"


def test_paypal_capture_con_id_atteso_viene_accettato(monkeypatch):
    fake_requests = FakeRequestsPayPalCapture(real_subscription_id="I-REAL123")
    monkeypatch.setattr(subscription_mod, "requests", fake_requests)
    monkeypatch.setattr(subscription_mod, "PLANS", PLAN_FAKE)

    repo = FakeUserRepo({"user-1": {
        "id": "user-1", "is_demo": False, "pending_paypal_subscription_id": "I-REAL123",
    }})
    service = SubscriptionService(repo=repo)

    result = run(service.paypal_capture({"id": "user-1"}, {"subscription_id": "I-REAL123"}))

    assert result == {"ok": True, "status": "active"}
    assert repo.users_by_id["user-1"]["subscription_status"] == "active"
    assert repo.users_by_id["user-1"]["paypal_subscription_id"] == "I-REAL123"
    # Ripulito dopo la cattura riuscita, non deve restare in giro.
    assert repo.users_by_id["user-1"]["pending_paypal_subscription_id"] is None


def test_paypal_capture_con_id_di_un_altro_utente_viene_rifiutato(monkeypatch):
    """Il caso centrale del fix: l'attaccante (user-2) non ha mai creato
    né si aspetta la subscription "I-VITTIMA" (creata da user-1), ma
    PayPal la confermerebbe comunque come reale e ACTIVE."""
    fake_requests = FakeRequestsPayPalCapture(real_subscription_id="I-VITTIMA")
    monkeypatch.setattr(subscription_mod, "requests", fake_requests)
    monkeypatch.setattr(subscription_mod, "PLANS", PLAN_FAKE)

    repo = FakeUserRepo({
        "user-1": {"id": "user-1", "is_demo": False, "pending_paypal_subscription_id": "I-VITTIMA"},
        "user-2": {"id": "user-2", "is_demo": False},  # attaccante: nessun id atteso
    })
    service = SubscriptionService(repo=repo)

    with pytest.raises(HTTPException) as exc_info:
        run(service.paypal_capture({"id": "user-2"}, {"subscription_id": "I-VITTIMA"}))

    assert exc_info.value.status_code == 403
    # Il conto dell'attaccante NON deve essere stato attivato.
    assert repo.users_by_id["user-2"].get("subscription_status") is None
    assert repo.users_by_id["user-2"].get("paypal_subscription_id") is None
    # Nemmeno quello della vittima deve essere stato toccato da questa chiamata.
    assert repo.users_by_id["user-1"].get("subscription_status") is None


def test_paypal_capture_senza_alcuna_richiesta_precedente_viene_rifiutato(monkeypatch):
    """Un utente che non ha mai chiamato create_paypal_subscription (nessun
    pending_paypal_subscription_id, nessun paypal_subscription_id
    pregresso) non può presentare NESSUN subscription_id valido."""
    fake_requests = FakeRequestsPayPalCapture(real_subscription_id="I-QUALSIASI")
    monkeypatch.setattr(subscription_mod, "requests", fake_requests)
    monkeypatch.setattr(subscription_mod, "PLANS", PLAN_FAKE)

    repo = FakeUserRepo({"user-3": {"id": "user-3", "is_demo": False}})
    service = SubscriptionService(repo=repo)

    with pytest.raises(HTTPException) as exc_info:
        run(service.paypal_capture({"id": "user-3"}, {"subscription_id": "I-QUALSIASI"}))

    assert exc_info.value.status_code == 403


def test_paypal_capture_riaccetta_lid_gia_legato_in_precedenza(monkeypatch):
    """Una ricattura sullo stesso abbonamento già attaccato all'utente
    (es. l'utente riclicca dopo un timeout, o il webhook è arrivato
    prima della capture) deve restare possibile: l'id è già "suo"."""
    fake_requests = FakeRequestsPayPalCapture(real_subscription_id="I-GIA-MIO", status="ACTIVE")
    monkeypatch.setattr(subscription_mod, "requests", fake_requests)
    monkeypatch.setattr(subscription_mod, "PLANS", PLAN_FAKE)

    repo = FakeUserRepo({"user-4": {
        "id": "user-4", "is_demo": False, "paypal_subscription_id": "I-GIA-MIO",
    }})
    service = SubscriptionService(repo=repo)

    result = run(service.paypal_capture({"id": "user-4"}, {"subscription_id": "I-GIA-MIO"}))

    assert result == {"ok": True, "status": "active"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
