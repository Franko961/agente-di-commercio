"""
Verifica che le email generate dal backend puntino sempre a FRONTEND_URL
(configurabile, es. https://salesfly.it) e mai a un dominio Netlify scritto
a mano — e che il link "Admin Dashboard" punti alla rotta reale /app/admin,
non a /admin (che non esiste nel frontend).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_frontend_url_usage.py -v
"""
import sys
import types
import asyncio

sys.path.insert(0, ".")

import services.auth_service as auth_service_mod
from services.auth_service import AuthService
import services.subscription_service as subscription_mod
from services.subscription_service import SubscriptionService
from core.config import FRONTEND_URL


def run(coro):
    return asyncio.run(coro)


async def _allow_always(*a, **kw):
    return True


async def _fake_seed_demo(user_id):
    return None


sent_emails = []


async def _capturing_send_email(to, subject, html):
    sent_emails.append({"to": to, "subject": subject, "html": html})
    return True


class FakeUserRepo:
    def __init__(self):
        self.inserted = []

    async def find_by_email(self, email):
        return None

    async def insert(self, doc):
        self.inserted.append(doc)
        return doc


def test_email_benvenuto_e_notifica_admin_usano_frontend_url_non_netlify(monkeypatch):
    from models.auth import RegisterIn
    sent_emails.clear()
    monkeypatch.setattr(auth_service_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(auth_service_mod.seed_service, "seed_demo", _fake_seed_demo)
    monkeypatch.setattr(auth_service_mod, "send_email", _capturing_send_email)
    service = AuthService(repo=FakeUserRepo())

    run(service.register(
        RegisterIn(email="nuovo@example.com", password="password123", name="Nuovo Utente"),
        ip_address="1.2.3.4",
    ))

    assert len(sent_emails) == 2  # benvenuto + notifica admin
    for mail in sent_emails:
        assert "netlify.app" not in mail["html"]
        assert FRONTEND_URL in mail["html"]

    admin_mail = next(m for m in sent_emails if "Nuovo utente registrato" in m["subject"])
    # La rotta admin reale è /app/admin (protetta da AdminRoute), non /admin.
    assert f"{FRONTEND_URL}/app/admin" in admin_mail["html"]


class FakeStripeCustomer:
    id = "cus_123"


class FakeStripeSession:
    url = "https://checkout.stripe.com/session123"


class FakeStripeModule(types.ModuleType):
    def __init__(self):
        super().__init__("stripe")
        self.api_key = None
        self.Customer = types.SimpleNamespace(create=lambda **kw: FakeStripeCustomer())
        self.checkout = types.SimpleNamespace(
            Session=types.SimpleNamespace(create=self._capture_session_create)
        )
        self.last_call = None

    def _capture_session_create(self, **kwargs):
        self.last_call = kwargs
        return FakeStripeSession()


class FakeSubUserRepo:
    async def find_by_id(self, uid):
        return {"id": uid, "email": "mario@example.com", "name": "Mario", "stripe_customer_id": "cus_existing"}

    async def update_by_id(self, uid, data):
        pass


def test_checkout_stripe_usa_frontend_url_come_fallback_se_return_url_assente(monkeypatch):
    monkeypatch.setattr(subscription_mod, "STRIPE_SECRET_KEY", "sk_test_fake")
    fake_stripe = FakeStripeModule()
    sys.modules["stripe"] = fake_stripe

    service = SubscriptionService(repo=FakeSubUserRepo())
    result = run(service.create_stripe_session({"id": "user-1", "email": "mario@example.com"}, {"plan": "base"}))

    assert result["url"] == "https://checkout.stripe.com/session123"
    assert fake_stripe.last_call["success_url"] == f"{FRONTEND_URL}/abbonamento?success=stripe"
    assert fake_stripe.last_call["cancel_url"] == f"{FRONTEND_URL}/abbonamento?cancelled=1"
    assert "netlify.app" not in fake_stripe.last_call["success_url"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
