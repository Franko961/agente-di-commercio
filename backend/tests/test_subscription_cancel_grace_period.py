"""
Verifica il fix della disdetta abbonamento: prima di questa modifica,
cancel_subscription() impostava subscription_status='cancelled' subito,
tagliando l'accesso all'istante — mentre il testo mostrato in
Subscription.jsx promette "l'accesso rimane attivo fino alla fine del
periodo pagato". Questi test verificano che ora sia davvero così, sia per
Stripe (cancel_at_period_end, data presa da current_period_end) sia per
PayPal (che non supporta una cancellazione differita: la data di fine
periodo si ricava da next_billing_time prima di cancellare subito), e che
i rispettivi webhook finalizzino/non finalizzino la cancellazione al
momento giusto.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_subscription_cancel_grace_period.py -v
"""
import sys
import asyncio
from datetime import datetime, timezone, timedelta

import pytest

sys.path.insert(0, ".")

import services.subscription_service as subscription_mod
from services.subscription_service import SubscriptionService
from core.subscription_utils import is_subscription_active


def run(coro):
    return asyncio.run(coro)


class FakeUserRepo:
    def __init__(self, users_by_id):
        self.users_by_id = users_by_id
        self.updates = []

    async def find_by_id(self, uid):
        return self.users_by_id.get(uid)

    async def update_by_id(self, uid, data):
        self.updates.append((uid, data))
        self.users_by_id[uid].update(data)

    async def update_by_stripe_subscription_id(self, sub_id, data):
        for u in self.users_by_id.values():
            if u.get("stripe_subscription_id") == sub_id:
                u.update(data)

    async def update_by_paypal_subscription_id(self, sub_id, data):
        for u in self.users_by_id.values():
            if u.get("paypal_subscription_id") == sub_id:
                u.update(data)

    async def find_by_paypal_subscription_id(self, sub_id):
        for u in self.users_by_id.values():
            if u.get("paypal_subscription_id") == sub_id:
                return u
        return None


class FakeWebhookEventsCollection:
    """Sostituisce la collection Mongo reale usata per l'idempotenza dei
    webhook PayPal, così il test non tocca un database vero."""

    def __init__(self):
        self.seen_ids = set()

    async def find_one(self, query):
        eid = query.get("event_id")
        return {"event_id": eid} if eid in self.seen_ids else None

    async def insert_one(self, doc):
        self.seen_ids.add(doc["event_id"])


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = str(self._json)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("http error")

    def json(self):
        return self._json


class FakeRequestsPayPal:
    """Sostituisce il modulo `requests` usato da subscription_service per le
    chiamate PayPal, senza colpire la rete reale."""

    def __init__(self, next_billing_time):
        self.next_billing_time = next_billing_time
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("POST", url))
        if "/oauth2/token" in url:
            return FakeResponse(200, {"access_token": "fake-token"})
        return FakeResponse(200, {})

    def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        return FakeResponse(200, {
            "status": "ACTIVE",
            "plan_id": "P-FAKE",
            "billing_info": {"next_billing_time": self.next_billing_time},
        })


class FakeRequest:
    """Doppio minimo di fastapi.Request per i test sui webhook: solo
    .headers (dict) e i due metodi async usati (.body/.json)."""

    def __init__(self, body_bytes=b"{}", json_data=None, headers=None):
        self._body = body_bytes
        self._json = json_data or {}
        self.headers = headers or {}

    async def body(self):
        return self._body

    async def json(self):
        return self._json


# ---------- is_subscription_active con cancel_at ----------

def test_active_senza_cancel_at_e_attivo():
    assert is_subscription_active({"subscription_status": "active"}) is True


def test_active_con_cancel_at_futuro_e_ancora_attivo():
    future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    assert is_subscription_active({"subscription_status": "active", "cancel_at": future}) is True


def test_active_con_cancel_at_passato_non_e_piu_attivo():
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert is_subscription_active({"subscription_status": "active", "cancel_at": past}) is False


# ---------- cancel_subscription: Stripe ----------

def test_cancel_stripe_non_taglia_subito_e_salva_cancel_at(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    future_ts = int((datetime.now(timezone.utc) + timedelta(days=12)).timestamp())

    class FakeStripeSubscription:
        @staticmethod
        def modify(sub_id, cancel_at_period_end=None):
            assert cancel_at_period_end is True
            return {"current_period_end": future_ts}

    fake_stripe_module = type("FakeStripe", (), {"api_key": None, "Subscription": FakeStripeSubscription})
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)

    user = {"id": "user-1", "is_demo": False, "stripe_subscription_id": "sub_123"}
    repo = FakeUserRepo({"user-1": dict(user)})
    service = SubscriptionService(repo=repo)

    result = run(service.cancel_subscription(user))

    assert result == {"ok": True}
    updated = repo.users_by_id["user-1"]
    assert "cancel_at" in updated
    assert updated.get("subscription_status") != "cancelled"


# ---------- cancel_subscription: PayPal ----------

def test_cancel_paypal_usa_next_billing_time_come_cancel_at(monkeypatch):
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_ID", "cid")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "")

    next_billing = (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fake_requests = FakeRequestsPayPal(next_billing)
    monkeypatch.setattr(subscription_mod, "requests", fake_requests)

    user = {"id": "user-2", "is_demo": False, "paypal_subscription_id": "I-FAKE123"}
    repo = FakeUserRepo({"user-2": dict(user)})
    service = SubscriptionService(repo=repo)

    result = run(service.cancel_subscription(user))

    assert result == {"ok": True}
    updated = repo.users_by_id["user-2"]
    assert updated.get("cancel_at") == next_billing
    assert updated.get("subscription_status") != "cancelled"
    # Deve aver davvero chiamato l'endpoint di cancellazione PayPal
    assert any(url.endswith("/cancel") for method, url in fake_requests.calls if method == "POST")


def test_cancel_senza_provider_configurato_cancella_subito(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_ID", "")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_SECRET", "")

    user = {"id": "user-3", "is_demo": False}
    repo = FakeUserRepo({"user-3": dict(user)})
    service = SubscriptionService(repo=repo)

    run(service.cancel_subscription(user))

    assert repo.users_by_id["user-3"].get("subscription_status") == "cancelled"


# ---------- Webhook Stripe: finalizza a fine periodo ----------

def test_webhook_stripe_subscription_deleted_finalizza_e_pulisce_cancel_at(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")

    fake_event = {"type": "customer.subscription.deleted", "data": {"object": {"id": "sub_456"}}}

    class FakeWebhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            return fake_event

    fake_stripe_module = type("FakeStripe", (), {"api_key": None, "Webhook": FakeWebhook})
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)

    repo = FakeUserRepo({"user-4": {
        "id": "user-4", "stripe_subscription_id": "sub_456",
        "subscription_status": "active", "cancel_at": "2026-01-01T00:00:00+00:00",
    }})
    service = SubscriptionService(repo=repo)

    request = FakeRequest(headers={"stripe-signature": "sig"})
    result = run(service.handle_stripe_webhook(request))

    assert result == {"ok": True}
    updated = repo.users_by_id["user-4"]
    assert updated["subscription_status"] == "cancelled"
    assert updated["cancel_at"] is None


# ---------- Webhook PayPal: non deve tagliare subito se cancel_at è già impostato ----------

def test_webhook_paypal_cancelled_non_taglia_se_cancel_at_gia_impostato(monkeypatch):
    monkeypatch.setattr(subscription_mod, "paypal_webhook_events", FakeWebhookEventsCollection())

    future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    repo = FakeUserRepo({"user-5": {
        "id": "user-5", "paypal_subscription_id": "I-ABC",
        "subscription_status": "active", "cancel_at": future,
    }})
    service = SubscriptionService(repo=repo)
    monkeypatch.setattr(service, "_verify_paypal_webhook_signature", lambda *a, **k: True)

    event = {"id": "evt-1", "event_type": "BILLING.SUBSCRIPTION.CANCELLED", "resource": {"id": "I-ABC"}}
    request = FakeRequest(json_data=event)

    result = run(service.handle_paypal_webhook(request))

    assert result == {"ok": True}
    assert repo.users_by_id["user-5"]["subscription_status"] == "active"


def test_webhook_paypal_cancelled_taglia_subito_se_cancellata_fuori_dalla_nostra_app(monkeypatch):
    monkeypatch.setattr(subscription_mod, "paypal_webhook_events", FakeWebhookEventsCollection())

    repo = FakeUserRepo({"user-6": {
        "id": "user-6", "paypal_subscription_id": "I-XYZ",
        "subscription_status": "active",
    }})
    service = SubscriptionService(repo=repo)
    monkeypatch.setattr(service, "_verify_paypal_webhook_signature", lambda *a, **k: True)

    event = {"id": "evt-2", "event_type": "BILLING.SUBSCRIPTION.CANCELLED", "resource": {"id": "I-XYZ"}}
    request = FakeRequest(json_data=event)

    result = run(service.handle_paypal_webhook(request))

    assert result == {"ok": True}
    assert repo.users_by_id["user-6"]["subscription_status"] == "cancelled"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
