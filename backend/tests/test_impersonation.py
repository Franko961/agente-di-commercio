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


def test_get_current_user_propaga_impersonation_started_at(monkeypatch):
    user_doc = {"id": "user-42", "email": "utente@esempio.it", "role": "agent", "subscription_status": "active"}
    monkeypatch.setattr(security_mod, "db", FakeDb(user_doc))

    before = datetime.now(timezone.utc)
    token = create_impersonation_token("admin-1", "user-42", "utente@esempio.it")
    result = run(get_current_user(FakeRequest(token)))
    after = datetime.now(timezone.utc)

    started_at = result["impersonation_started_at"]
    assert isinstance(started_at, datetime)
    # iat ha risoluzione al secondo: tolleranza di un secondo su entrambi i lati
    assert before - timedelta(seconds=1) <= started_at <= after + timedelta(seconds=1)


def test_impersonazione_esente_dal_gate_trial_anche_con_abbonamento_scaduto(monkeypatch):
    """Un admin che entra per assistenza non deve essere bloccato dallo stato
    di abbonamento (scaduto/annullato) dell'utente che sta aiutando — anzi è
    spesso proprio il motivo per cui serve assistenza. Prima di questo fix,
    get_current_user applicava il gate trial anche alle sessioni di
    impersonificazione, rendendo inutilizzabile il gestionale (ogni
    chiamata API rispondeva 402) per qualunque utente con abbonamento non
    attivo — cioè gli utenti che più probabilmente hanno bisogno di aiuto."""
    user_doc = {
        "id": "user-42", "email": "utente@esempio.it", "role": "agent",
        "subscription_status": "cancelled",
    }
    monkeypatch.setattr(security_mod, "db", FakeDb(user_doc))
    token = create_impersonation_token("admin-1", "user-42", "utente@esempio.it")

    result = run(get_current_user(FakeRequest(token)))

    assert result["id"] == "user-42"


def test_login_normale_con_abbonamento_scaduto_resta_bloccato(monkeypatch):
    """Controllo di non-regressione: l'esenzione sopra riguarda SOLO le
    sessioni di impersonificazione, non deve allentare il gate per l'utente
    che accede con il proprio login normale."""
    from core.security import create_access_token
    user_doc = {
        "id": "user-42", "email": "utente@esempio.it", "role": "agent",
        "subscription_status": "cancelled",
    }
    monkeypatch.setattr(security_mod, "db", FakeDb(user_doc))
    token = create_access_token("user-42", "utente@esempio.it")

    with pytest.raises(HTTPException) as exc_info:
        run(get_current_user(FakeRequest(token)))
    assert exc_info.value.status_code == 402


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

    token, email = run(service.impersonate_user("user-42", ADMIN_ACTOR, category="assistenza_richiesta"))

    assert email == "utente@esempio.it"
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    assert payload["sub"] == "user-42"
    assert payload["impersonated_by"] == "admin-1"


def test_impersonate_user_traccia_laudit_log(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, fake_db = build_service(monkeypatch, [ADMIN_ACTOR, target])

    run(service.impersonate_user("user-42", ADMIN_ACTOR, category="diagnosi_problema"))

    assert len(fake_db.admin_audit_log.inserted) == 1
    entry = fake_db.admin_audit_log.inserted[0]
    assert entry["actor"] == "admin@salesfly.it"
    assert entry["action"] == "impersonate_user"
    assert entry["target_user_id"] == "user-42"
    assert entry["detail"]["target_email"] == "utente@esempio.it"
    assert entry["detail"]["category"] == "diagnosi_problema"


def test_impersonate_user_default_e_modalita_view(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, fake_db = build_service(monkeypatch, [ADMIN_ACTOR, target])

    token, _ = run(service.impersonate_user("user-42", ADMIN_ACTOR, category="verifica_configurazione"))

    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    assert payload["impersonation_mode"] == "view"
    assert fake_db.admin_audit_log.inserted[0]["detail"]["mode"] == "view"
    assert "reason" not in fake_db.admin_audit_log.inserted[0]["detail"]


def test_impersonate_user_rifiuta_mode_non_valida(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, _ = build_service(monkeypatch, [ADMIN_ACTOR, target])

    with pytest.raises(HTTPException) as exc_info:
        run(service.impersonate_user("user-42", ADMIN_ACTOR, mode="delete-everything", category="assistenza_richiesta"))
    assert exc_info.value.status_code == 400


def test_impersonate_user_rifiuta_categoria_mancante_anche_in_sola_lettura(monkeypatch):
    """La sola lettura non modifica nulla, ma deve comunque dichiarare
    almeno una categoria rapida nell'audit log — non è esente dal controllo."""
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, _ = build_service(monkeypatch, [ADMIN_ACTOR, target])

    with pytest.raises(HTTPException) as exc_info:
        run(service.impersonate_user("user-42", ADMIN_ACTOR, mode="view", category=None))
    assert exc_info.value.status_code == 400


def test_impersonate_user_rifiuta_categoria_non_valida(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, _ = build_service(monkeypatch, [ADMIN_ACTOR, target])

    with pytest.raises(HTTPException) as exc_info:
        run(service.impersonate_user("user-42", ADMIN_ACTOR, mode="view", category="motivo_a_caso"))
    assert exc_info.value.status_code == 400


def test_impersonate_user_edit_richiede_un_motivo(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, _ = build_service(monkeypatch, [ADMIN_ACTOR, target])

    with pytest.raises(HTTPException) as exc_info:
        run(service.impersonate_user("user-42", ADMIN_ACTOR, mode="edit", category="controllo_amministrativo"))
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException):
        run(service.impersonate_user("user-42", ADMIN_ACTOR, mode="edit", category="controllo_amministrativo", reason="   "))


def test_impersonate_user_edit_con_motivo_riesce_e_traccia_il_motivo(monkeypatch):
    target = {"id": "user-42", "email": "utente@esempio.it", "role": "agent"}
    service, fake_db = build_service(monkeypatch, [ADMIN_ACTOR, target])

    token, _ = run(service.impersonate_user(
        "user-42", ADMIN_ACTOR, mode="edit", category="controllo_amministrativo",
        reason="Richiesta assistenza telefonica: correggere ordine",
    ))

    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    assert payload["impersonation_mode"] == "edit"
    detail = fake_db.admin_audit_log.inserted[0]["detail"]
    assert detail["mode"] == "edit"
    assert detail["category"] == "controllo_amministrativo"
    assert detail["reason"] == "Richiesta assistenza telefonica: correggere ordine"


# ---------- admin_service.record_impersonation_exit ----------

def test_record_impersonation_exit_traccia_azione_e_dettagli(monkeypatch):
    service, fake_db = build_service(monkeypatch, [ADMIN_ACTOR])
    started_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    run(service.record_impersonation_exit(
        "admin@salesfly.it", "user-42", "utente@esempio.it", "edit", started_at,
    ))

    assert len(fake_db.admin_audit_log.inserted) == 1
    entry = fake_db.admin_audit_log.inserted[0]
    assert entry["actor"] == "admin@salesfly.it"
    assert entry["action"] == "exit_impersonation"
    assert entry["target_user_id"] == "user-42"
    detail = entry["detail"]
    assert detail["target_email"] == "utente@esempio.it"
    assert detail["mode"] == "edit"
    assert detail["started_at"] == started_at.isoformat()
    assert detail["ended_at"] is not None


def test_record_impersonation_exit_calcola_la_durata(monkeypatch):
    service, fake_db = build_service(monkeypatch, [ADMIN_ACTOR])
    started_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    run(service.record_impersonation_exit(
        "admin@salesfly.it", "user-42", "utente@esempio.it", "view", started_at,
    ))

    duration = fake_db.admin_audit_log.inserted[0]["detail"]["duration_seconds"]
    assert 295 <= duration <= 305  # ~5 minuti, tolleranza per il tempo di esecuzione del test


def test_record_impersonation_exit_senza_started_at_non_fallisce(monkeypatch):
    service, fake_db = build_service(monkeypatch, [ADMIN_ACTOR])

    run(service.record_impersonation_exit(
        "admin@salesfly.it", "user-42", "utente@esempio.it", "view", None,
    ))

    detail = fake_db.admin_audit_log.inserted[0]["detail"]
    assert detail["started_at"] is None
    assert detail["duration_seconds"] is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
