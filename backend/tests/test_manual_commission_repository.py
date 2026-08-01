"""
Verifica ManualCommissionRepository: le provvigioni inserite manualmente
dall'utente, una per (utente, mese "YYYY-MM"), che si sommano al totale
calcolato dagli ordini (vedi services/commission_service.py) per coprire
provvigioni non tracciate tramite il flusso ordini del CRM.

Usa un finto collection MongoDB che replica update_one(upsert=True): crea
il documento se non esiste (rispettando $setOnInsert per created_at),
altrimenti aggiorna solo i campi in $set — stesso approccio già validato
per gli altri repository di questo progetto.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_manual_commission_repository.py -v
"""
import sys
import asyncio

import pytest

sys.path.insert(0, ".")

from repositories.manual_commission_repository import ManualCommissionRepository


def run(coro):
    return asyncio.run(coro)


class FakeMongoCollection:
    def __init__(self):
        self.docs = {}  # (user_id, period) -> dict

    def find(self, query, _projection=None):
        matches = [d for d in self.docs.values() if d["user_id"] == query["user_id"]]
        return _FakeCursor(matches)

    async def update_one(self, query, update, upsert=False):
        key = (query["user_id"], query["period"])
        existing = self.docs.get(key)
        if existing is None:
            if not upsert:
                return
            new_doc = {**update.get("$setOnInsert", {}), **update.get("$set", {})}
            self.docs[key] = new_doc
        else:
            existing.update(update.get("$set", {}))

    async def delete_one(self, query):
        self.docs.pop((query["user_id"], query["period"]), None)


class _FakeCursor:
    def __init__(self, items):
        self._items = items

    async def to_list(self, limit):
        return self._items[:limit]


def build_repo():
    repo = ManualCommissionRepository()
    repo.collection = FakeMongoCollection()
    return repo


def test_upsert_crea_il_documento_se_non_esiste():
    repo = build_repo()
    run(repo.upsert("user-1", "2026-08", 450))
    docs = run(repo.find_many("user-1"))
    assert len(docs) == 1
    assert docs[0]["period"] == "2026-08"
    assert docs[0]["amount"] == 450
    assert docs[0]["created_at"] is not None


def test_upsert_sullo_stesso_mese_aggiorna_invece_di_duplicare():
    repo = build_repo()
    run(repo.upsert("user-1", "2026-08", 450))
    run(repo.upsert("user-1", "2026-08", 600))
    docs = run(repo.find_many("user-1"))
    assert len(docs) == 1
    assert docs[0]["amount"] == 600


def test_upsert_created_at_non_cambia_su_aggiornamento_successivo():
    repo = build_repo()
    run(repo.upsert("user-1", "2026-08", 450))
    created_at_originale = run(repo.find_many("user-1"))[0]["created_at"]
    run(repo.upsert("user-1", "2026-08", 600))
    created_at_dopo = run(repo.find_many("user-1"))[0]["created_at"]
    assert created_at_originale == created_at_dopo


def test_mesi_diversi_restano_indipendenti():
    repo = build_repo()
    run(repo.upsert("user-1", "2026-07", 100))
    run(repo.upsert("user-1", "2026-08", 200))
    docs = run(repo.find_many("user-1"))
    assert {d["period"]: d["amount"] for d in docs} == {"2026-07": 100, "2026-08": 200}


def test_find_many_non_restituisce_dati_di_un_altro_utente():
    repo = build_repo()
    run(repo.upsert("user-1", "2026-08", 450))
    run(repo.upsert("user-2", "2026-08", 999))
    docs = run(repo.find_many("user-1"))
    assert len(docs) == 1
    assert docs[0]["amount"] == 450


def test_delete_rimuove_il_documento():
    repo = build_repo()
    run(repo.upsert("user-1", "2026-08", 450))
    run(repo.delete("user-1", "2026-08"))
    assert run(repo.find_many("user-1")) == []


def test_delete_di_un_mese_mai_creato_non_fallisce():
    repo = build_repo()
    run(repo.delete("user-1", "2026-08"))  # non deve sollevare eccezioni


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
