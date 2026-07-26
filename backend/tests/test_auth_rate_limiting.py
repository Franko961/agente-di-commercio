"""
Verifica il rate limiting aggiunto a login e checkout-expired: prima nessuno
dei due aveva un limite di tentativi, nonostante entrambi verifichino una
password — un attaccante poteva provare password illimitate su un'email nota
(brute-force) o scandire molte combinazioni email+password dallo stesso IP
(credential stuffing), senza mai incontrare un blocco.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_auth_rate_limiting.py -v
"""
import sys
import asyncio

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

from core.security import hash_password
from models.auth import LoginIn
import services.auth_service as auth_service_mod
from services.auth_service import AuthService
import services.subscription_service as subscription_mod
from services.subscription_service import SubscriptionService


def run(coro):
    return asyncio.run(coro)


async def _allow_always(*a, **kw):
    return True


async def _deny_always(*a, **kw):
    return False


class FakeUserRepo:
    def __init__(self, users_by_email=None):
        self.users_by_email = users_by_email or {}

    async def find_by_email(self, email):
        return self.users_by_email.get(email)


def _user(email="mario@example.com", password="password-corretta"):
    return {
        "id": "user-1", "email": email, "name": "Mario Rossi",
        "password_hash": hash_password(password), "role": "agent",
    }


# ---------- login ----------

def test_login_corretto_funziona(monkeypatch):
    monkeypatch.setattr(auth_service_mod, "check_and_record", _allow_always)
    service = AuthService(repo=FakeUserRepo({"mario@example.com": _user()}))

    token, out = run(service.login(LoginIn(email="mario@example.com", password="password-corretta")))

    assert token
    assert out["email"] == "mario@example.com"


def test_login_password_sbagliata_rifiutata(monkeypatch):
    monkeypatch.setattr(auth_service_mod, "check_and_record", _allow_always)
    service = AuthService(repo=FakeUserRepo({"mario@example.com": _user()}))

    with pytest.raises(HTTPException) as exc_info:
        run(service.login(LoginIn(email="mario@example.com", password="sbagliata")))
    assert exc_info.value.status_code == 401


def test_troppi_tentativi_per_email_bloccano_il_login_prima_di_verificare_la_password(monkeypatch):
    """Il caso che ha motivato il fix: senza rate limit, un attaccante può
    provare password illimitate sulla stessa email nota."""
    monkeypatch.setattr(auth_service_mod, "check_and_record", _deny_always)
    service = AuthService(repo=FakeUserRepo({"mario@example.com": _user()}))

    with pytest.raises(HTTPException) as exc_info:
        run(service.login(LoginIn(email="mario@example.com", password="qualsiasi")))
    assert exc_info.value.status_code == 429


def test_rate_limit_login_usa_email_e_ip_come_chiavi(monkeypatch):
    calls = []

    async def _tracking_check(kind, key, max_attempts, window_minutes):
        calls.append((kind, key))
        return True

    monkeypatch.setattr(auth_service_mod, "check_and_record", _tracking_check)
    service = AuthService(repo=FakeUserRepo({"mario@example.com": _user()}))

    run(service.login(LoginIn(email="mario@example.com", password="password-corretta"), ip_address="9.9.9.9"))

    assert ("login_email", "mario@example.com") in calls
    assert ("login_ip", "9.9.9.9") in calls


# ---------- checkout-expired (verifica anch'esso una password) ----------

class FakeStripeCapableService(SubscriptionService):
    async def create_stripe_session(self, user, payload):
        return {"url": "https://stripe.example/session"}


def test_checkout_expired_password_corretta_procede(monkeypatch):
    monkeypatch.setattr(subscription_mod, "check_and_record", _allow_always)
    service = FakeStripeCapableService(repo=FakeUserRepo({"mario@example.com": _user()}))

    result = run(service.create_checkout_for_expired_account(
        {"email": "mario@example.com", "password": "password-corretta", "plan": "base"},
        ip_address="1.2.3.4",
    ))
    assert result == {"url": "https://stripe.example/session"}


def test_checkout_expired_troppi_tentativi_bloccati(monkeypatch):
    monkeypatch.setattr(subscription_mod, "check_and_record", _deny_always)
    service = FakeStripeCapableService(repo=FakeUserRepo({"mario@example.com": _user()}))

    with pytest.raises(HTTPException) as exc_info:
        run(service.create_checkout_for_expired_account(
            {"email": "mario@example.com", "password": "qualsiasi", "plan": "base"},
            ip_address="1.2.3.4",
        ))
    assert exc_info.value.status_code == 429


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
