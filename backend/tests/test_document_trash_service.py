"""
Test per la pulizia periodica del cestino documenti
(services.document_trash_service): cancella per davvero (DB + file S3) i
documenti soft-deleted (documents ed employee_documents) più vecchi della
retention configurata, lasciando intatti quelli soft-deleted più di recente
e quelli non eliminati.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_document_trash_service.py -v
"""
import sys
import asyncio
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

import services.document_trash_service as trash_mod
from services.document_trash_service import DocumentTrashService


def run(coro):
    return asyncio.run(coro)


def iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, n):
        return self._docs[:n]


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []
        self.delete_many_calls = []

    def find(self, query, projection=None):
        def matches(d):
            for k, v in query.items():
                if isinstance(v, dict) and "$lt" in v:
                    if not (k in d and d[k] < v["$lt"]):
                        return False
                elif d.get(k) != v:
                    return False
            return True
        return FakeCursor([d for d in self.docs if matches(d)])

    async def delete_many(self, query):
        self.delete_many_calls.append(dict(query))
        ids = set(query["id"]["$in"])
        before = len(self.docs)
        self.docs = [d for d in self.docs if d["id"] not in ids]
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


def build_fake_db():
    fake_db = FakeDb()
    fake_db.documents.docs = [
        {"id": "d-old", "is_deleted": True, "deleted_at": iso_days_ago(31), "storage_path": "salesfly/uploads/u1/old.pdf"},
        {"id": "d-recent", "is_deleted": True, "deleted_at": iso_days_ago(5), "storage_path": "salesfly/uploads/u1/recent.pdf"},
        {"id": "d-active", "is_deleted": False, "storage_path": "salesfly/uploads/u1/active.pdf"},
        {"id": "d-old-nopath", "is_deleted": True, "deleted_at": iso_days_ago(60), "storage_path": None},
    ]
    fake_db.employee_documents.docs = [
        {"id": "ed-old", "is_deleted": True, "deleted_at": iso_days_ago(45), "storage_path": "salesfly/uploads/u1/employees/e1/old.pdf"},
        {"id": "ed-recent", "is_deleted": True, "deleted_at": iso_days_ago(1), "storage_path": "salesfly/uploads/u1/employees/e1/recent.pdf"},
    ]
    return fake_db


def build_service(monkeypatch, fake_db, storage_delete_impl=None):
    monkeypatch.setattr(trash_mod, "db", fake_db)
    deleted_paths = []

    def default_impl(path):
        deleted_paths.append(path)

    monkeypatch.setattr(trash_mod, "storage_delete", storage_delete_impl or default_impl)
    return DocumentTrashService(), deleted_paths


def test_purge_cancella_solo_i_soft_deleted_oltre_la_retention(monkeypatch):
    fake_db = build_fake_db()
    service, deleted_paths = build_service(monkeypatch, fake_db)

    purged = run(service.purge_expired(retention_days=30))

    remaining_ids = {d["id"] for d in fake_db.documents.docs} | {d["id"] for d in fake_db.employee_documents.docs}
    assert "d-old" not in remaining_ids
    assert "d-old-nopath" not in remaining_ids
    assert "ed-old" not in remaining_ids
    # Non ancora scaduti, e il documento mai eliminato: intatti.
    assert "d-recent" in remaining_ids
    assert "d-active" in remaining_ids
    assert "ed-recent" in remaining_ids
    assert purged == 3


def test_purge_cancella_il_file_s3_solo_quando_presente(monkeypatch):
    fake_db = build_fake_db()
    service, deleted_paths = build_service(monkeypatch, fake_db)

    run(service.purge_expired(retention_days=30))

    assert sorted(deleted_paths) == sorted([
        "salesfly/uploads/u1/old.pdf",
        "salesfly/uploads/u1/employees/e1/old.pdf",
    ])


def test_purge_non_cancella_il_record_se_s3_fallisce(monkeypatch):
    fake_db = build_fake_db()

    def failing_delete(path):
        raise RuntimeError("S3 non raggiungibile")

    service, _ = build_service(monkeypatch, fake_db, storage_delete_impl=failing_delete)

    purged = run(service.purge_expired(retention_days=30))

    # Nessun record con storage_path cancellato: solo d-old-nopath (che non
    # ha un file da cancellare) viene rimosso.
    remaining_ids = {d["id"] for d in fake_db.documents.docs} | {d["id"] for d in fake_db.employee_documents.docs}
    assert "d-old" in remaining_ids
    assert "ed-old" in remaining_ids
    assert "d-old-nopath" not in remaining_ids
    assert purged == 1


def test_purge_senza_documenti_scaduti_non_fa_nulla(monkeypatch):
    fake_db = FakeDb()
    fake_db.documents.docs = [
        {"id": "d1", "is_deleted": True, "deleted_at": iso_days_ago(1), "storage_path": "x"},
    ]
    service, deleted_paths = build_service(monkeypatch, fake_db)

    purged = run(service.purge_expired(retention_days=30))

    assert purged == 0
    assert deleted_paths == []
    assert len(fake_db.documents.docs) == 1


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
