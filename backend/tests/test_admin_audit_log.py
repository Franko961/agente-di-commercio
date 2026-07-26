"""
Test per l'audit amministrativo aggiunto ad admin_service: ogni azione
sensibile (promozione ad admin, modifica/cancellazione utente) deve lasciare
una traccia in admin_audit_log, distinta dal registro azioni AI già
esistente (quello riguarda gli agenti, questo riguarda l'amministrazione
della piattaforma).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_admin_audit_log.py -v
"""
import sys
import asyncio
import os

sys.path.insert(0, ".")

import services.admin_service as admin_service_mod
from services.admin_service import AdminService


def run(coro):
    return asyncio.run(coro)


async def _allow_always(*a, **kw):
    return True


async def _deny_always(*a, **kw):
    return False


class FakeAuditCollection:
    def __init__(self):
        self.inserted = []

    async def insert_one(self, doc):
        self.inserted.append(doc)


class FakeDb:
    def __init__(self):
        self.admin_audit_log = FakeAuditCollection()


class FakeAdminRepo:
    def __init__(self):
        self.updated = []
        self.deleted = []

    async def promote_by_email(self, email):
        return email == "franco@test.it"

    async def update_user(self, uid, data):
        self.updated.append((uid, data))

    async def delete_user(self, uid):
        self.deleted.append(uid)


def build_service(monkeypatch):
    fake_db = FakeDb()
    monkeypatch.setattr(admin_service_mod, "db", fake_db)
    repo = FakeAdminRepo()
    return AdminService(repo=repo), fake_db, repo


def test_make_admin_traccia_audit(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "s3gr3t0")
    monkeypatch.setattr(admin_service_mod, "check_and_record", _allow_always)
    service, fake_db, repo = build_service(monkeypatch)

    run(service.make_admin("franco@test.it", "s3gr3t0"))

    assert len(fake_db.admin_audit_log.inserted) == 1
    entry = fake_db.admin_audit_log.inserted[0]
    assert entry["action"] == "make_admin"
    assert entry["detail"]["email"] == "franco@test.it"


def test_update_user_traccia_chi_ha_fatto_la_modifica(monkeypatch):
    service, fake_db, repo = build_service(monkeypatch)
    admin_actor = {"id": "admin-1", "email": "admin@salesfly.it"}

    run(service.update_user("u-42", {"plan": "pro"}, admin=admin_actor))

    assert repo.updated == [("u-42", {"plan": "pro"})]
    entry = fake_db.admin_audit_log.inserted[0]
    assert entry["actor"] == "admin@salesfly.it"
    assert entry["action"] == "update_user"
    assert entry["target_user_id"] == "u-42"
    assert entry["detail"] == {"plan": "pro"}


def test_delete_user_traccia_lazione(monkeypatch):
    service, fake_db, repo = build_service(monkeypatch)
    admin_actor = {"id": "admin-1", "email": "admin@salesfly.it"}

    run(service.delete_user("u-99", admin=admin_actor))

    assert repo.deleted == ["u-99"]
    entry = fake_db.admin_audit_log.inserted[0]
    assert entry["action"] == "delete_user"
    assert entry["target_user_id"] == "u-99"


def test_update_user_senza_admin_esplicito_non_crasha(monkeypatch):
    service, fake_db, repo = build_service(monkeypatch)

    run(service.update_user("u-1", {"role": "agent"}))

    entry = fake_db.admin_audit_log.inserted[0]
    assert entry["actor"] == "sconosciuto"
