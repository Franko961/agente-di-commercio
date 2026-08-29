"""
Test per il reset periodico dell'account demo condiviso
(services.demo_reset_service): svuota tutte le collection user-scoped
dell'account/i con is_demo=True (riusando la stessa lista di
gdpr_service.USER_SCOPED_COLLECTIONS), cancella i file S3 collegati, e
riseminata con seed_service — SENZA toccare il documento utente stesso
(a differenza della cancellazione account GDPR) e SENZA toccare i dati di
altri utenti.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_demo_reset_service.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

import services.demo_reset_service as demo_reset_mod
from services.demo_reset_service import DemoResetService
from services.gdpr_service import USER_SCOPED_COLLECTIONS


def run(coro):
    return asyncio.run(coro)


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, n):
        return self._docs[:n]


class FakeCollection:
    def __init__(self):
        self.docs = []
        self.delete_many_calls = []

    def find(self, query, projection=None):
        docs = [d for d in self.docs if all(d.get(k) == v for k, v in query.items())]
        return FakeCursor(docs)

    async def delete_many(self, query):
        self.delete_many_calls.append(dict(query))
        before = len(self.docs)
        self.docs = [d for d in self.docs if d.get("user_id") != query.get("user_id")]
        return type("R", (), {"deleted_count": before - len(self.docs)})()


class FakeDb:
    def __init__(self):
        self._collections = {}

    def _get(self, name):
        if name not in self._collections:
            self._collections[name] = FakeCollection()
        return self._collections[name]

    def __getattr__(self, name):
        return self._get(name)

    def __getitem__(self, name):
        return self._get(name)


class FakeSeedService:
    def __init__(self):
        self.seeded_for = []

    async def seed_demo(self, user_id):
        self.seeded_for.append(user_id)


def build_fake_db():
    fake_db = FakeDb()
    fake_db.users.docs = [
        {"id": "demo-1", "email": "demo@salesfly.it", "is_demo": True},
        {"id": "user-normale", "email": "mario@example.com", "is_demo": False},
    ]
    fake_db.clients.docs = [
        {"id": "c1", "user_id": "demo-1", "company_name": "Cliente demo modificato"},
        {
            "id": "c2",
            "user_id": "user-normale",
            "company_name": "Cliente di un utente vero",
        },
    ]
    fake_db.documents.docs = [
        {
            "id": "d1",
            "user_id": "demo-1",
            "storage_path": "salesfly/uploads/demo-1/doc1.pdf",
        },
        {
            "id": "d2",
            "user_id": "demo-1",
            "storage_path": None,
        },  # record senza file reale
        {
            "id": "d3",
            "user_id": "user-normale",
            "storage_path": "salesfly/uploads/user-normale/doc.pdf",
        },
    ]
    return fake_db


def build_service(monkeypatch, fake_db, fake_seed):
    monkeypatch.setattr(demo_reset_mod, "db", fake_db)
    monkeypatch.setattr(demo_reset_mod, "seed_service", fake_seed)
    deleted_paths = []
    monkeypatch.setattr(
        demo_reset_mod, "storage_delete", lambda path: deleted_paths.append(path)
    )
    return DemoResetService(), deleted_paths


def test_reset_svuota_solo_i_dati_dellaccount_demo(monkeypatch):
    fake_db = build_fake_db()
    fake_seed = FakeSeedService()
    service, deleted_paths = build_service(monkeypatch, fake_db, fake_seed)

    count = run(service.reset_all_demo_accounts())

    assert count == 1
    # Ogni collection user-scoped ha ricevuto un delete_many per l'account demo.
    for collection_name in USER_SCOPED_COLLECTIONS.values():
        calls = fake_db._collections[collection_name].delete_many_calls
        assert {"user_id": "demo-1"} in calls
    # I dati dell'utente normale restano intatti.
    assert any(c["user_id"] == "user-normale" for c in fake_db.clients.docs)
    assert not any(c["user_id"] == "demo-1" for c in fake_db.clients.docs)


def test_reset_cancella_solo_i_file_s3_dellaccount_demo(monkeypatch):
    fake_db = build_fake_db()
    fake_seed = FakeSeedService()
    service, deleted_paths = build_service(monkeypatch, fake_db, fake_seed)

    run(service.reset_all_demo_accounts())

    assert deleted_paths == [
        "salesfly/uploads/demo-1/doc1.pdf"
    ]  # non doc2 (senza path), non doc3 (altro utente)


def test_reset_riseminata_solo_laccount_demo(monkeypatch):
    fake_db = build_fake_db()
    fake_seed = FakeSeedService()
    service, _ = build_service(monkeypatch, fake_db, fake_seed)

    run(service.reset_all_demo_accounts())

    assert fake_seed.seeded_for == ["demo-1"]


def test_reset_non_tocca_il_documento_utente(monkeypatch):
    fake_db = build_fake_db()
    fake_seed = FakeSeedService()
    service, _ = build_service(monkeypatch, fake_db, fake_seed)

    run(service.reset_all_demo_accounts())

    # users non è in USER_SCOPED_COLLECTIONS: nessun delete_many è mai stato
    # chiamato su di essa, il documento demo-1 resta al suo posto.
    assert fake_db.users.delete_many_calls == []
    assert any(u["id"] == "demo-1" for u in fake_db.users.docs)


def test_reset_senza_alcun_account_demo_non_fa_nulla(monkeypatch):
    fake_db = build_fake_db()
    fake_db.users.docs = [
        {"id": "user-normale", "email": "mario@example.com", "is_demo": False}
    ]
    fake_seed = FakeSeedService()
    service, deleted_paths = build_service(monkeypatch, fake_db, fake_seed)

    count = run(service.reset_all_demo_accounts())

    assert count == 0
    assert fake_seed.seeded_for == []
    assert deleted_paths == []


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
