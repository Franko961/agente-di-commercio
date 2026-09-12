"""
Verifica migrations._003_fix_lead_status_from_ai_tool.run: i lead creati
dal tool AI con lo status non valido "aperto" (bug reale, vedi
tests/test_ai_add_lead_status.py e il commento nella migrazione stessa)
devono essere riportati a "nuovo" — così tornano visibili nella pipeline
Kanban, che filtra strettamente per status in LEAD_STATUSES.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_lead_status_backfill.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

import migrations._003_fix_lead_status_from_ai_tool as migration_mod
from migrations._003_fix_lead_status_from_ai_tool import run as fix_lead_status


def run(coro):
    return asyncio.run(coro)


class FakeLeadsCollection:
    def __init__(self, docs):
        self.docs = {d["id"]: d for d in docs}
        self.update_many_calls = []

    async def update_many(self, query, update):
        self.update_many_calls.append((query, update))
        nin = query["status"]["$nin"]
        matched = 0
        for doc in self.docs.values():
            if doc.get("status") not in nin:
                doc.update(update["$set"])
                matched += 1
        return matched


class FakeDb:
    def __init__(self, docs):
        self.leads = FakeLeadsCollection(docs)


def test_riporta_a_nuovo_i_lead_con_status_non_valido(monkeypatch):
    docs = [
        {"id": "l1", "status": "aperto"},  # il bug reale
        {"id": "l2", "status": "contattato"},  # già valido, invariato
        {"id": "l3"},  # nessun campo status affatto, stesso trattamento
    ]
    fake_db = FakeDb(docs)
    monkeypatch.setattr(migration_mod, "db", fake_db)

    run(fix_lead_status())

    assert fake_db.leads.docs["l1"]["status"] == "nuovo"
    assert fake_db.leads.docs["l2"]["status"] == "contattato"
    assert fake_db.leads.docs["l3"]["status"] == "nuovo"


def test_nessuna_azione_se_tutti_gli_status_sono_gia_validi(monkeypatch):
    docs = [{"id": "l1", "status": "nuovo"}, {"id": "l2", "status": "vinto"}]
    fake_db = FakeDb(docs)
    monkeypatch.setattr(migration_mod, "db", fake_db)

    run(fix_lead_status())

    assert fake_db.leads.docs["l1"]["status"] == "nuovo"
    assert fake_db.leads.docs["l2"]["status"] == "vinto"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
