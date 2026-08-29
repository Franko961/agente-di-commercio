"""
Verifica che l'account demo condiviso non possa avviare o modificare
pagamenti/abbonamenti reali (Stripe/PayPal): _forbid_if_demo blocca
create_stripe_session, create_paypal_subscription, paypal_capture e
cancel_subscription prima di qualunque chiamata verso i provider esterni.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_subscription_demo_protection.py -v
"""

import asyncio
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

import services.subscription_service as subscription_mod
from services.subscription_service import SubscriptionService


def run(coro):
    return asyncio.run(coro)


class FakeUserRepo:
    def __init__(self, users_by_id):
        self.users_by_id = users_by_id

    async def find_by_id(self, uid):
        return self.users_by_id.get(uid)


DEMO_USER = {"id": "user-demo", "email": "demo@salesfly.it", "is_demo": True}
NORMAL_USER = {"id": "user-1", "email": "mario@example.com", "is_demo": False}


def _fail_if_called(*a, **k):
    raise AssertionError(
        "nessuna chiamata reale al provider di pagamento doveva partire per l'account demo"
    )


def test_create_stripe_session_bloccata_per_demo(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    service = SubscriptionService(repo=FakeUserRepo({"user-demo": DEMO_USER}))

    with pytest.raises(HTTPException) as exc_info:
        run(service.create_stripe_session(DEMO_USER, {"plan": "base"}))
    assert exc_info.value.status_code == 403


def test_create_paypal_subscription_bloccata_per_demo(monkeypatch):
    service = SubscriptionService(repo=FakeUserRepo({"user-demo": DEMO_USER}))

    with pytest.raises(HTTPException) as exc_info:
        run(service.create_paypal_subscription(DEMO_USER, {"plan": "base"}))
    assert exc_info.value.status_code == 403


def test_paypal_capture_bloccata_per_demo(monkeypatch):
    service = SubscriptionService(repo=FakeUserRepo({"user-demo": DEMO_USER}))

    with pytest.raises(HTTPException) as exc_info:
        run(service.paypal_capture(DEMO_USER, {"subscription_id": "sub-1"}))
    assert exc_info.value.status_code == 403


def test_cancel_subscription_bloccata_per_demo(monkeypatch):
    service = SubscriptionService(repo=FakeUserRepo({"user-demo": DEMO_USER}))

    with pytest.raises(HTTPException) as exc_info:
        run(service.cancel_subscription(DEMO_USER))
    assert exc_info.value.status_code == 403


def test_create_stripe_session_funziona_per_utente_normale(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")

    class FakeCustomer:
        id = "cus_123"

    class FakeSession:
        url = "https://stripe.example/session"

    class FakeStripeModule:
        api_key = None
        Customer = type("C", (), {"create": staticmethod(lambda **k: FakeCustomer())})
        checkout = type(
            "Checkout",
            (),
            {
                "Session": type(
                    "Session", (), {"create": staticmethod(lambda **k: FakeSession())}
                )
            },
        )

    monkeypatch.setitem(sys.modules, "stripe", FakeStripeModule)
    repo = FakeUserRepo({"user-1": {**NORMAL_USER, "name": "Mario"}})

    async def _update_by_id(uid, data):
        repo.users_by_id[uid].update(data)

    repo.update_by_id = _update_by_id

    service = SubscriptionService(repo=repo)
    result = run(service.create_stripe_session(NORMAL_USER, {"plan": "base"}))

    assert result == {"url": "https://stripe.example/session"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
