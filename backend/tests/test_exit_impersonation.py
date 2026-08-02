"""
Verifica POST /api/auth/exit-impersonation (routers/auth.py):
- traccia esplicitamente la FINE della sessione (admin_service.impersonate_user
  traccia solo l'inizio) con admin, utente, modalità, inizio, fine, durata;
- ricontrolla che l'admin sia TUTTORA admin prima di riemettere il token di
  ritorno, non solo che l'account esista — un ruolo revocato durante la
  sessione non deve fruttare comunque un accesso senza nuovo login.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_exit_impersonation.py -v
"""
import sys
import asyncio
from datetime import datetime, timezone, timedelta

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

import routers.auth as auth_router_mod
from routers.auth import exit_impersonation


def run(coro):
    return asyncio.run(coro)


class FakeResponse:
    def __init__(self):
        self.cookies = []

    def set_cookie(self, *a, **k):
        self.cookies.append((a, k))


class FakeUserRepo:
    def __init__(self, users_by_id):
        self.users_by_id = users_by_id

    async def find_by_id(self, uid):
        return self.users_by_id.get(uid)


class FakeAdminService:
    def __init__(self):
        self.calls = []

    async def record_impersonation_exit(self, actor, target_user_id, target_email, mode, started_at):
        self.calls.append({
            "actor": actor, "target_user_id": target_user_id, "target_email": target_email,
            "mode": mode, "started_at": started_at,
        })


ADMIN = {"id": "admin-1", "email": "admin@salesfly.it", "role": "admin"}
DEMOTED_ADMIN = {"id": "admin-1", "email": "admin@salesfly.it", "role": "agent"}

IMPERSONATED_USER = {
    "id": "user-42", "email": "utente@esempio.it",
    "impersonated_by": "admin-1", "impersonation_mode": "view",
    "impersonation_started_at": datetime.now(timezone.utc) - timedelta(minutes=12),
}


def test_rifiuta_se_nessuna_impersonificazione_attiva(monkeypatch):
    monkeypatch.setattr(auth_router_mod, "user_repository", FakeUserRepo({}))
    monkeypatch.setattr(auth_router_mod, "admin_service", FakeAdminService())

    with pytest.raises(HTTPException) as exc_info:
        run(exit_impersonation(FakeResponse(), user={"id": "user-42"}))
    assert exc_info.value.status_code == 400


def test_rifiuta_se_admin_non_trovato(monkeypatch):
    monkeypatch.setattr(auth_router_mod, "user_repository", FakeUserRepo({}))
    monkeypatch.setattr(auth_router_mod, "admin_service", FakeAdminService())

    with pytest.raises(HTTPException) as exc_info:
        run(exit_impersonation(FakeResponse(), user=IMPERSONATED_USER))
    assert exc_info.value.status_code == 404


def test_rifiuta_se_il_ruolo_admin_e_stato_revocato(monkeypatch):
    monkeypatch.setattr(auth_router_mod, "user_repository", FakeUserRepo({"admin-1": DEMOTED_ADMIN}))
    fake_admin_service = FakeAdminService()
    monkeypatch.setattr(auth_router_mod, "admin_service", fake_admin_service)

    with pytest.raises(HTTPException) as exc_info:
        run(exit_impersonation(FakeResponse(), user=IMPERSONATED_USER))
    assert exc_info.value.status_code == 403
    # Nessun token deve essere stato tracciato/rilasciato per questo tentativo
    assert fake_admin_service.calls == []


def test_uscita_riuscita_riemette_il_token_e_traccia_luscita(monkeypatch):
    monkeypatch.setattr(auth_router_mod, "user_repository", FakeUserRepo({"admin-1": ADMIN}))
    fake_admin_service = FakeAdminService()
    monkeypatch.setattr(auth_router_mod, "admin_service", fake_admin_service)
    response = FakeResponse()

    result = run(exit_impersonation(response, user=IMPERSONATED_USER))

    assert result == {"ok": True}
    assert len(response.cookies) == 1

    assert len(fake_admin_service.calls) == 1
    call = fake_admin_service.calls[0]
    assert call["actor"] == "admin@salesfly.it"
    assert call["target_user_id"] == "user-42"
    assert call["target_email"] == "utente@esempio.it"
    assert call["mode"] == "view"
    assert call["started_at"] == IMPERSONATED_USER["impersonation_started_at"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
