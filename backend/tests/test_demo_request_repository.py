"""
Verifica DemoRequestRepository.delete_older_than(): la pulizia periodica
delle richieste demo vecchie (vedi startup_service._demo_request_cleanup_loop).
created_at è salvato come stringa ISO (non una data BSON nativa), quindi il
filtro è un confronto testuale — questo test verifica che tale confronto
selezioni davvero solo i record più vecchi del cutoff, non quelli più recenti
o esattamente al limite.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_demo_request_repository.py -v
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, ".")

from repositories.demo_request_repository import DemoRequestRepository


def run(coro):
    return asyncio.run(coro)


def _iso(dt):
    return dt.isoformat()


class _DeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


class FakeMongoCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    async def delete_many(self, query):
        cutoff = query["created_at"]["$lt"]
        before = len(self.docs)
        self.docs = [d for d in self.docs if not (d["created_at"] < cutoff)]
        return _DeleteResult(deleted_count=before - len(self.docs))


def build_repo(docs=None):
    repo = DemoRequestRepository()
    repo.collection = FakeMongoCollection(docs)
    return repo


def test_elimina_solo_le_richieste_piu_vecchie_del_cutoff():
    now = datetime.now(timezone.utc)
    repo = build_repo(
        [
            {"id": "r1", "created_at": _iso(now - timedelta(days=800))},
            {"id": "r2", "created_at": _iso(now - timedelta(days=100))},
        ]
    )
    cutoff = _iso(now - timedelta(days=730))

    deleted = run(repo.delete_older_than(cutoff))

    assert deleted == 1
    assert [d["id"] for d in repo.collection.docs] == ["r2"]


def test_richiesta_esattamente_al_cutoff_non_viene_eliminata():
    now = datetime.now(timezone.utc)
    cutoff_dt = now - timedelta(days=730)
    repo = build_repo([{"id": "r1", "created_at": _iso(cutoff_dt)}])

    deleted = run(repo.delete_older_than(_iso(cutoff_dt)))

    assert deleted == 0
    assert len(repo.collection.docs) == 1


def test_nessuna_richiesta_vecchia_non_elimina_nulla():
    now = datetime.now(timezone.utc)
    repo = build_repo([{"id": "r1", "created_at": _iso(now - timedelta(days=1))}])

    deleted = run(repo.delete_older_than(_iso(now - timedelta(days=730))))

    assert deleted == 0
    assert len(repo.collection.docs) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
