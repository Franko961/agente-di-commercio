"""
Verifica che handle_stripe_webhook() fallisca in modo sicuro (fail-closed)
se STRIPE_WEBHOOK_SECRET non è configurato, invece di verificare la firma
con una chiave HMAC vuota — che chiunque potrebbe calcolare, rendendo
falsificabile qualunque evento Stripe (es. un checkout.session.completed
fabbricato che attiverebbe un piano a pagamento gratis). Stesso principio
già in vigore per PayPal (_verify_paypal_webhook_signature rifiuta se
PAYPAL_WEBHOOK_ID manca).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_stripe_webhook_secret_failclosed.py -v
"""
import sys
import asyncio

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

import services.subscription_service as subscription_mod
from services.subscription_service import SubscriptionService
from tests.test_subscription_cancel_grace_period import FakeUserRepo, FakeRequest


def run(coro):
    return asyncio.run(coro)


def test_webhook_stripe_rifiuta_se_webhook_secret_vuoto(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(subscription_mod, "STRIPE_WEBHOOK_SECRET", "")

    called = {"construct_event": False}

    class FakeWebhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            called["construct_event"] = True
            return {"id": "evt-x", "type": "checkout.session.completed", "data": {"object": {}}}

    fake_stripe_module = type("FakeStripe", (), {"api_key": None, "Webhook": FakeWebhook})
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)

    service = SubscriptionService(repo=FakeUserRepo({}))

    with pytest.raises(HTTPException) as exc_info:
        run(service.handle_stripe_webhook(FakeRequest(headers={"stripe-signature": "qualunque"})))

    assert exc_info.value.status_code == 500
    # Non deve nemmeno tentare di verificare la firma con la chiave vuota.
    assert called["construct_event"] is False


def test_webhook_stripe_funziona_normalmente_con_webhook_secret_configurato(monkeypatch):
    """Controllo di non-regressione: il percorso normale (secret presente)
    non deve essere toccato da questo fix."""
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(subscription_mod, "STRIPE_WEBHOOK_SECRET", "whsec_fake")
    monkeypatch.setattr(subscription_mod, "stripe_webhook_events", type(
        "FakeColl", (), {
            "find_one": staticmethod(lambda q: _none_coro()),
            "insert_one": staticmethod(lambda d: _none_coro()),
        },
    )())

    fake_event = {"id": "evt-y", "type": "checkout.session.completed",
                  "data": {"object": {"metadata": {}, "subscription": None}}}

    class FakeWebhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            assert secret == "whsec_fake"
            return fake_event

    fake_stripe_module = type("FakeStripe", (), {"api_key": None, "Webhook": FakeWebhook})
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)

    service = SubscriptionService(repo=FakeUserRepo({}))

    result = run(service.handle_stripe_webhook(FakeRequest(headers={"stripe-signature": "sig"})))

    assert result == {"ok": True}


async def _none_coro():
    return None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
