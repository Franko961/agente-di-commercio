"""
Verifica il fix di cancel_subscription(): se un provider di pagamento è
configurato per l'utente ma la chiamata di cancellazione non è confermata
riuscita (eccezione, o una risposta HTTP non-2xx da PayPal — che
`requests` non segnala da sola come eccezione), il codice NON deve più
scrivere subscription_status="cancelled" nel nostro DB. Prima di questo
fix, un fallimento di Stripe/PayPal durante la disdetta faceva comunque
cancellare l'abbonamento lato nostro (tagliando subito l'accesso), mentre
il provider non era mai stato davvero istruito a fermare gli addebiti:
il cliente perdeva l'accesso E continuava a pagare.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_cancel_subscription_provider_failure.py -v
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


def test_cancel_stripe_fallito_non_marca_cancellato_e_solleva_errore(monkeypatch):
    """Il caso centrale del fix: stripe.Subscription.modify solleva
    un'eccezione (es. errore di rete/Stripe momentaneamente giù) -> non
    deve più cadere nel ramo 'nessuna data -> cancella subito'."""
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_ID", "")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_SECRET", "")

    class FakeStripeSubscription:
        @staticmethod
        def modify(sub_id, cancel_at_period_end=None):
            raise Exception("Stripe temporaneamente non disponibile")

    fake_stripe_module = type("FakeStripe", (), {"api_key": None, "Subscription": FakeStripeSubscription})
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)

    user = {"id": "user-1", "is_demo": False, "stripe_subscription_id": "sub_123"}
    repo = FakeUserRepo({"user-1": dict(user)})
    service = SubscriptionService(repo=repo)

    with pytest.raises(HTTPException) as exc_info:
        run(service.cancel_subscription(user))

    assert exc_info.value.status_code == 502
    # Nessuna scrittura che tagli l'accesso: l'utente resta come prima.
    assert repo.users_by_id["user-1"].get("subscription_status") != "cancelled"
    assert "cancel_at" not in repo.users_by_id["user-1"]


def test_cancel_paypal_con_status_non_2xx_non_marca_cancellato(monkeypatch):
    """requests.post non solleva un'eccezione da sola per una risposta 400:
    va controllato lo status_code esplicitamente."""
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_ID", "cid")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "")

    class FailingCancelRequests:
        def post(self, url, **kwargs):
            if "/oauth2/token" in url:
                return FakeResponse(200, {"access_token": "fake-token"})
            if url.endswith("/cancel"):
                return FakeResponse(400, {"message": "Subscription status invalid"})
            return FakeResponse(200, {})

        def get(self, url, **kwargs):
            return FakeResponse(200, {"status": "ACTIVE", "billing_info": {}})

    monkeypatch.setattr(subscription_mod, "requests", FailingCancelRequests())

    user = {"id": "user-2", "is_demo": False, "paypal_subscription_id": "I-FAKE"}
    repo = FakeUserRepo({"user-2": dict(user)})
    service = SubscriptionService(repo=repo)

    with pytest.raises(HTTPException) as exc_info:
        run(service.cancel_subscription(user))

    assert exc_info.value.status_code == 502
    assert repo.users_by_id["user-2"].get("subscription_status") != "cancelled"


def test_cancel_stripe_riuscito_senza_current_period_end_cancella_subito(monkeypatch):
    """Caso limite legittimo: la chiamata Stripe riesce davvero (nessuna
    eccezione) ma non restituisce current_period_end — qui è corretto
    cancellare subito, la cancellazione lato Stripe è comunque avvenuta."""
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_ID", "")
    monkeypatch.setattr(subscription_mod, "PAYPAL_CLIENT_SECRET", "")

    class FakeStripeSubscription:
        @staticmethod
        def modify(sub_id, cancel_at_period_end=None):
            return {}  # nessun current_period_end nella risposta

    fake_stripe_module = type("FakeStripe", (), {"api_key": None, "Subscription": FakeStripeSubscription})
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)

    user = {"id": "user-3", "is_demo": False, "stripe_subscription_id": "sub_789"}
    repo = FakeUserRepo({"user-3": dict(user)})
    service = SubscriptionService(repo=repo)

    result = run(service.cancel_subscription(user))

    assert result == {"ok": True}
    assert repo.users_by_id["user-3"]["subscription_status"] == "cancelled"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
