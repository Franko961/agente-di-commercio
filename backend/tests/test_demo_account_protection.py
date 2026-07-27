"""
Verifica il fix critico sull'account demo condiviso (is_demo=True):

- forbid_demo_write blocca l'utente demo, lascia passare un utente normale;
- forgot_password non deve mai emettere/inviare un token di reset per
  l'account demo (credenziali pubbliche: un token valido permetterebbe a
  chiunque di prenderne il controllo);
- reset_password rifiuta comunque un token che risolva a un utente is_demo,
  come difesa in profondità nel caso ne esistesse uno per altra via.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_demo_account_protection.py -v
"""
import sys
import asyncio

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

from core.security import forbid_demo_write, hash_password, hash_reset_token
from models.auth import ForgotPasswordIn, ResetPasswordIn
import services.auth_service as auth_service_mod
from services.auth_service import AuthService


def run(coro):
    return asyncio.run(coro)


async def _allow_always(*a, **kw):
    return True


class FakeUserRepo:
    def __init__(self, users_by_email=None):
        self.users_by_email = users_by_email or {}
        self.updates = []

    async def find_by_email(self, email):
        return self.users_by_email.get(email)

    async def find_by_reset_token_hash(self, token_hash):
        for u in self.users_by_email.values():
            if u.get("reset_token_hash") == token_hash:
                return u
        return None

    async def update_by_id(self, uid, data):
        self.updates.append((uid, data))
        for u in self.users_by_email.values():
            if u["id"] == uid:
                u.update(data)


def _demo_user():
    return {
        "id": "user-demo", "email": "demo@salesfly.it", "is_demo": True,
        "password_hash": hash_password("password-nota-pubblicamente"), "role": "agent",
    }


def _normal_user():
    return {
        "id": "user-1", "email": "mario@example.com", "is_demo": False,
        "password_hash": hash_password("password-corretta"), "role": "agent",
    }


# ---------- forbid_demo_write ----------

def test_forbid_demo_write_blocca_utente_demo():
    with pytest.raises(HTTPException) as exc_info:
        run(forbid_demo_write(user=_demo_user()))
    assert exc_info.value.status_code == 403


def test_forbid_demo_write_lascia_passare_utente_normale():
    result = run(forbid_demo_write(user=_normal_user()))
    assert result["id"] == "user-1"


# ---------- forgot_password ----------

async def _fail_if_called(*a, **kw):
    raise AssertionError("send_email non doveva essere chiamato per l'account demo")


def test_forgot_password_non_emette_token_per_account_demo(monkeypatch):
    monkeypatch.setattr(auth_service_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(auth_service_mod, "send_email", _fail_if_called)
    repo = FakeUserRepo({"demo@salesfly.it": _demo_user()})
    service = AuthService(repo=repo)

    result = run(service.forgot_password(ForgotPasswordIn(email="demo@salesfly.it")))

    assert result["ok"] is True
    assert repo.updates == []  # nessun reset_token_hash scritto


def test_forgot_password_funziona_normalmente_per_utente_non_demo(monkeypatch):
    monkeypatch.setattr(auth_service_mod, "check_and_record", _allow_always)
    sent = []

    async def _track_send(to, subject, html):
        sent.append(to)

    monkeypatch.setattr(auth_service_mod, "send_email", _track_send)
    repo = FakeUserRepo({"mario@example.com": _normal_user()})
    service = AuthService(repo=repo)

    result = run(service.forgot_password(ForgotPasswordIn(email="mario@example.com")))

    assert result["ok"] is True
    assert len(repo.updates) == 1
    assert sent == ["mario@example.com"]


# ---------- reset_password ----------

def test_reset_password_rifiuta_token_che_risolve_a_utente_demo(monkeypatch):
    monkeypatch.setattr(auth_service_mod, "check_and_record", _allow_always)
    demo = _demo_user()
    demo["reset_token_hash"] = hash_reset_token("token-in-chiaro")
    from datetime import datetime, timezone, timedelta
    demo["reset_token_expires"] = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    repo = FakeUserRepo({"demo@salesfly.it": demo})
    service = AuthService(repo=repo)

    with pytest.raises(HTTPException) as exc_info:
        run(service.reset_password(ResetPasswordIn(token="token-in-chiaro", new_password="nuovapassword123")))
    assert exc_info.value.status_code == 400


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
