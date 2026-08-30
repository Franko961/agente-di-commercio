"""
Verifica migrations._002_manual_commission_ids.run: i documenti
manual_commissions creati prima dell'introduzione del CRUD per id (vecchio
upsert per (user_id, period), senza campo id) devono ricevere un id reale
all'avvio — altrimenti, con l'indice univoco (user_id, period) rimosso, due
righe senza id potrebbero collidere sul fallback sintetico
"manual:{period}" di commission_service.normalize_manual_commission.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_manual_commission_id_backfill.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

import migrations._002_manual_commission_ids as startup_service_mod
from migrations._002_manual_commission_ids import run as backfill_manual_commission_ids


def run(coro):
    return asyncio.run(coro)


class FakeCursor:
    def __init__(self, docs):
        self._iter = iter(docs)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class FakeManualCommissionsCollection:
    def __init__(self, docs):
        self.docs = {d["_id"]: d for d in docs}
        self.update_calls = []

    def find(self, query, _projection=None):
        assert query == {"id": {"$exists": False}}
        matches = [d for d in self.docs.values() if "id" not in d]
        return FakeCursor(matches)

    async def update_one(self, query, update):
        self.update_calls.append((query, update))
        doc = self.docs[query["_id"]]
        doc.update(update["$set"])


class FakeDb:
    def __init__(self, docs):
        self.manual_commissions = FakeManualCommissionsCollection(docs)


def test_backfilla_id_sui_documenti_che_non_ce_lhanno(monkeypatch):
    docs = [
        {
            "_id": "mongo-1",
            "user_id": "user-1",
            "period": "2026-08",
            "amount": 300,
        },  # legacy, nessun id
        {
            "_id": "mongo-2",
            "user_id": "user-1",
            "period": "2026-08",
            "amount": 150,
            "id": "already-has-one",
        },
    ]
    fake_db = FakeDb(docs)
    monkeypatch.setattr(startup_service_mod, "db", fake_db)

    run(backfill_manual_commission_ids())

    assert len(fake_db.manual_commissions.update_calls) == 1
    query, update = fake_db.manual_commissions.update_calls[0]
    assert query == {"_id": "mongo-1"}
    assert "id" in update["$set"]
    assert update["$set"]["id"]  # non vuoto


def test_i_backfillati_ottengono_id_diversi_anche_con_lo_stesso_periodo(monkeypatch):
    """Il caso concreto che la migrazione previene: due righe legacy senza
    id, stesso periodo — prima dell'indice univoco rimosso non potevano
    coesistere, ora sì, quindi devono ricevere id DISTINTI per non
    collidere nel fallback sintetico basato su period."""
    docs = [
        {"_id": "mongo-1", "user_id": "user-1", "period": "2026-08", "amount": 300},
        {"_id": "mongo-2", "user_id": "user-1", "period": "2026-08", "amount": 150},
    ]
    fake_db = FakeDb(docs)
    monkeypatch.setattr(startup_service_mod, "db", fake_db)

    run(backfill_manual_commission_ids())

    ids = {doc["id"] for doc in fake_db.manual_commissions.docs.values()}
    assert len(ids) == 2


def test_nessuna_azione_se_tutti_i_documenti_hanno_gia_un_id(monkeypatch):
    docs = [
        {
            "_id": "mongo-1",
            "user_id": "user-1",
            "period": "2026-08",
            "amount": 300,
            "id": "abc",
        }
    ]
    fake_db = FakeDb(docs)
    monkeypatch.setattr(startup_service_mod, "db", fake_db)

    run(backfill_manual_commission_ids())

    assert fake_db.manual_commissions.update_calls == []


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
