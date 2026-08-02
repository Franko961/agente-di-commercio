"""
Verifica il meccanismo di impersonificazione (core/security.py +
services/admin_service.py): un admin può entrare nel gestionale di un
utente per assistenza (es. richiesta telefonica di modificare qualcosa),
senza dover conoscere la sua password.

Copre:
- create_impersonation_token genera un token con lo stesso "sub"/email
  dell'utente target, più il claim impersonated_by (l'admin originale) e
  una scadenza breve (IMPERSONATION_TOKEN_TTL_MINUTES, non i 7 giorni del
  token normale — vedi il motivo nel commento della costante).
- get_current_user propaga impersonated_by sul dict utente ritornato, così
  ogni risposta che include l'utente (es. /api/auth/me) porta con sé
  l'informazione, non solo l'endpoint dove la sessione è iniziata.
- admin_service.impersonate_user: rifiuta l'auto-impersonificazione, un
  utente inesistente, un altro admin come bersaglio; traccia l'azione
  nell'audit log.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_impersonation.py -v
"""
import sys
import asyncio
from datetime import datetime, timezone, timedelta

import jwt
import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

from core.security import create_impersonation_token, get_current_user, forbid_demo_write, IMPERSONATION_TOKEN_TTL_MINUTES
from core.config import JWT_SECRET, JWT_ALG
import core.security as security_mod


def run(coro):
    return asyncio.run(coro)


# ---------- create_impersonation_token ----------

def test_token_autentica_come_lutente_target_non_come_ladmin():
    token = create_impersonation_token("admin-1", "user-42", "utente@esempio.it")
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    assert payload["sub"] == "user-42"
    assert payload["email"] == "utente@esempio.it"


def test_token_porta_il_claim_impersonated_by():
    token = create_impersonation_token("admin-1", "user-42", "utente@esempio.it")
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    assert payload["impersonated_by"] == "admin-1"


def test_token_scade_dopo_il_ttl_di_impersonificazione_non_7_giorni():
    token = create_impersonation_token("admin-1", "user-42", "utente@esempio.it")
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    assert exp < now + timedelta(days=1)
    assert exp > now + timedelta(minutes=IMPERSONATION_TOKEN_TTL_MINUTES - 1)


def test_token_e_view_per_default():
    token = create_impersonation_token("admin-1", "user-42", "utente@esempio.it")
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    assert payload["impersonation_mode"] == "view"


def test_token_porta_la_mode_edit_se_richiesta():
    token = create_impersonation_token("admin-1", "user-42", "utente@esempio.it", mode="edit")
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    assert payload["impersonation_mode"] == "edit"


# ---------- get_current_user: propagazione di impersonated_by ----------

class FakeUsersCollection:
    def __init__(self, doc):
        self.doc = doc

    async def find_one(self, query, _projection=None):
        return dict(self.doc) if self.doc.get("id") == query.get("id") else None


class FakeDb:
    def __init__(self, user_doc):
        self.users = FakeUsersCollection(user_doc)


class FakeRequest:
    def __init__(self, token):
        self.cookies = {"access_token": token}
        self.headers = {}
        self.url = type("U", (), {"path": "/api/clients"})()


def test_get_current_user_propaga_impersonated_by(monkeypatch):
    user_doc = {"id": "user-42", "email": "utente@esempio.it", "role": "agent", "subscription_status": "active"}
    monkeypatch.setattr(security_mod, "db", FakeDb(user_doc))

    token = create_impersonation_token("admin-1", "user-42", "utente@esempio.it")
    result = run(get_current_user(FakeRequest(token)))

    assert result["impersonated_by"] == "admin-1"


def test_get_current_user_propaga_impersonation_mode(monkeypatch):
    user_doc = {"id": "user-42", "email": "utente@esempio.it", "role": "agent", "subscription_status": "active"}
    monkeypatch.setattr(security_mod, "db", FakeDb(user_doc))

    token = create_impersonation_token("admin-1", "user-42", "utente@esempio.it", mode="edit")
    result = run(get_current_user(FakeRequest(token)))

    assert result["impersonation_mode"] == "edit"


def test_get_current_user_normale_non_ha_impersonated_by(monkeypatch):
    from core.security import create_access_token
    user_doc = {"id": "user-42", "email": "utente@esempio.it", "role": "agent", "subscription_status": "active"}
    monkeypatch.setattr(security_mod, "db", FakeDb(user_doc))

    token = create_access_token("user-42", "utente@esempio.it")
    result = run(get_current_user(FakeRequest(token)))

    assert "impersonated_by" not in result


# ---------- forbid_demo_write: blocca scrittura anche in impersonificazione "view" ----------

def test_forbid_demo_write_blocca_impersonificazione_in_sola_lettura():
    user = {"id": "user-42", "impersonated_by": "admin-1", "impersonation_mode": "view"}
    with pytest.raises(HTTPException) as exc_info:
        run(forbid_demo_write(user))
    assert exc_info.value.status_code == 403


def test_forbid_demo_write_permette_impersonificazione_in_modifica():
    user = {"id": "user-42", "impersonated_by": "admin-1", "impersonation_mode": "edit"}
    result = run(forbid_demo_write(user))
    assert result == user


def test_forbid_demo_write_permette_utente_normale():
    user = {"id": "user-1"}
    result = run(forbid_demo_write(user))
    assert result == user


# ---------- admin_service.impersonate_user ----------

import services.admin_service as admin_service_mod
from services.admin_service import AdminService


class FakeAuditCollection:
    def __init__(self):
        self.inserted = []

    async def insert_one(self, doc):
        self.inserted.append(doc)


class FakeAuditDb:
    def __init__(self):
        self.admin_audit_log = FakeAuditCollection()


class FakeUserRepo:
    def __init__(self, users):
        self._users = {u["id"]: u for u in users}

    async def find_by_id(self, uid):
        return self._users.get(uid)


def build_service(monkeypatch, users):
    fake_db = FakeAuditDb()
    monkeypatch.setattr(admin_service_mod, "db", fake_db)
    monkeypatch.setattr(admin_service_mod, "user_repository", FakeUserRepo(users))
    return AdminService(repo=None), fake_db


ADMIN_ACTOR = {"id": "admin-1", "email": "admin@salesfly.it"}


def test_impersonate_user_rifiuta_se_stesso(monkeypatch):
    service, _ = build_service(monkeypatch, [ADMIN_ACTOR])
    with pytest.raises(HTTPException) as exc_info:
        run(service.impersonate_user("admin-1", ADMIN_ACTOR))
    assert exc_info.value.status_code == 400


def test_impersonate_user_rifiuta_utente_inesistente(monkeypatch):
    service, _ = build_service(monkeypatch, [ADMIN_ACTOR])
    with pytest.raises(HTTPException) as exc_info:
        run(service.impersonate_user("non-esiste", ADMIN_ACTOR))
    assert exc_info.value.status_code == 404


def test_impersonate_user_rifiuta_un_altro_admin(monkeypatch):
    other_admin = {"id": "admin-2", "email": "altro-admin@salesfly.it", "role": "admin"}
    service, _ = build_service(monkeypatch, [ADMIN_ACTOR, other_admin])
    with pytest.raises(HTTPException) as exc_info:
        run(service.impersonate_user("admin-2", ADMIN_ACTOR))
    assert exc_info.value.status_code == 403


def test_impersonate_user_riuscito_ritorna_token_ed_email(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, fake_db = build_service(monkeypatch, [ADMIN_ACTOR, target])

    token, email = run(service.impersonate_user("user-42", ADMIN_ACTOR))

    assert email == "utente@esempio.it"
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    assert payload["sub"] == "user-42"
    assert payload["impersonated_by"] == "admin-1"


def test_impersonate_user_traccia_laudit_log(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, fake_db = build_service(monkeypatch, [ADMIN_ACTOR, target])

    run(service.impersonate_user("user-42", ADMIN_ACTOR))

    assert len(fake_db.admin_audit_log.inserted) == 1
    entry = fake_db.admin_audit_log.inserted[0]
    assert entry["actor"] == "admin@salesfly.it"
    assert entry["action"] == "impersonate_user"
    assert entry["target_user_id"] == "user-42"
    assert entry["detail"]["target_email"] == "utente@esempio.it"


def test_impersonate_user_default_e_modalita_view(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, fake_db = build_service(monkeypatch, [ADMIN_ACTOR, target])

    token, _ = run(service.impersonate_user("user-42", ADMIN_ACTOR))

    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    assert payload["impersonation_mode"] == "view"
    assert fake_db.admin_audit_log.inserted[0]["detail"]["mode"] == "view"
    assert "reason" not in fake_db.admin_audit_log.inserted[0]["detail"]


def test_impersonate_user_rifiuta_mode_non_valida(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, _ = build_service(monkeypatch, [ADMIN_ACTOR, target])

    with pytest.raises(HTTPException) as exc_info:
        run(service.impersonate_user("user-42", ADMIN_ACTOR, mode="delete-everything"))
    assert exc_info.value.status_code == 400


def test_impersonate_user_edit_richiede_un_motivo(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, _ = build_service(monkeypatch, [ADMIN_ACTOR, target])

    with pytest.raises(HTTPException) as exc_info:
        run(service.impersonate_user("user-42", ADMIN_ACTOR, mode="edit"))
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException):
        run(service.impersonate_user("user-42", ADMIN_ACTOR, mode="edit", reason="   "))


def test_impersonate_user_edit_con_motivo_riesce_e_traccia_il_motivo(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, fake_db = build_service(monkeypatch, [ADMIN_ACTOR, target])

    token, _ = run(service.impersonate_user("user-42", ADMIN_ACTOR, mode="edit", reason="Richiesta assistenza telefonica: correggere ordine"))

    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    assert payload["impersonation_mode"] == "edit"
    detail = fake_db.admin_audit_log.inserted[0]["detail"]
    assert detail["mode"] == "edit"
    assert detail["reason"] == "Richiesta assistenza telefonica: correggere ordine"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
