"""
Test per services/reconciliation_service.py: rileva (senza riparare) le
incoerenze tra le spese generate automaticamente da un compenso Personale o
un costo Flotta e il documento che le ha generate — possibili perché quel
flusso non usa una transazione Mongo (vedi employee_compensation_service.py
/ vehicle_cost_service.py).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_reconciliation_service.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

import services.reconciliation_service as reconciliation_mod
from services.reconciliation_service import ReconciliationService


def run(coro):
    return asyncio.run(coro)


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, n):
        return self._docs[:n]


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    def find(self, query, projection=None):
        def matches(d):
            return all(d.get(k) == v for k, v in query.items())

        return FakeCursor([d for d in self.docs if matches(d)])


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


def build_service(monkeypatch, fake_db):
    monkeypatch.setattr(reconciliation_mod, "db", fake_db)
    return ReconciliationService()


def test_nessuna_incoerenza_quando_tutto_e_collegato(monkeypatch):
    fake_db = FakeDb()
    fake_db.expenses.docs = [
        {
            "id": "e1",
            "user_id": "u1",
            "source": "personale",
            "employee_compensation_id": "c1",
        },
        {"id": "e2", "user_id": "u1", "source": "flotta", "vehicle_cost_id": "vc1"},
    ]
    fake_db.employee_compensation.docs = [
        {"id": "c1", "user_id": "u1", "expense_id": "e1"}
    ]
    fake_db.vehicle_costs.docs = [{"id": "vc1", "user_id": "u1", "expense_id": "e2"}]
    service = build_service(monkeypatch, fake_db)

    result = run(service.find_inconsistencies())

    assert result == {"orphan_expenses": [], "orphan_links": []}


def test_trova_spesa_personale_orfana(monkeypatch):
    fake_db = FakeDb()
    fake_db.expenses.docs = [
        {
            "id": "e1",
            "user_id": "u1",
            "source": "personale",
            "employee_compensation_id": "c-non-esiste",
        },
    ]
    fake_db.employee_compensation.docs = []
    fake_db.vehicle_costs.docs = []
    service = build_service(monkeypatch, fake_db)

    result = run(service.find_inconsistencies())

    assert result["orphan_expenses"] == [
        {"expense_id": "e1", "user_id": "u1", "source": "personale"}
    ]
    assert result["orphan_links"] == []


def test_trova_spesa_flotta_orfana(monkeypatch):
    fake_db = FakeDb()
    fake_db.expenses.docs = [
        {"id": "e1", "user_id": "u1", "source": "flotta", "vehicle_cost_id": None},
    ]
    fake_db.employee_compensation.docs = []
    fake_db.vehicle_costs.docs = []
    service = build_service(monkeypatch, fake_db)

    result = run(service.find_inconsistencies())

    assert result["orphan_expenses"] == [
        {"expense_id": "e1", "user_id": "u1", "source": "flotta"}
    ]


def test_trova_compenso_senza_spesa_collegata(monkeypatch):
    fake_db = FakeDb()
    fake_db.expenses.docs = []
    fake_db.employee_compensation.docs = [
        {"id": "c1", "user_id": "u1", "expense_id": "e-non-esiste"}
    ]
    fake_db.vehicle_costs.docs = []
    service = build_service(monkeypatch, fake_db)

    result = run(service.find_inconsistencies())

    assert result["orphan_links"] == [
        {"id": "c1", "user_id": "u1", "source": "personale"}
    ]
    assert result["orphan_expenses"] == []


def test_trova_costo_flotta_senza_spesa_collegata(monkeypatch):
    fake_db = FakeDb()
    fake_db.expenses.docs = []
    fake_db.employee_compensation.docs = []
    fake_db.vehicle_costs.docs = [
        {"id": "vc1", "user_id": "u1", "expense_id": "e-non-esiste"}
    ]
    service = build_service(monkeypatch, fake_db)

    result = run(service.find_inconsistencies())

    assert result["orphan_links"] == [
        {"id": "vc1", "user_id": "u1", "source": "flotta"}
    ]


def test_non_confonde_spese_di_altre_source(monkeypatch):
    # Una spesa manuale dell'agente (source assente/altro) non deve mai
    # comparire come "orfana": il controllo riguarda solo le spese generate
    # automaticamente da Personale/Flotta.
    fake_db = FakeDb()
    fake_db.expenses.docs = [
        {"id": "e1", "user_id": "u1", "source": None, "category": "vitto"},
    ]
    fake_db.employee_compensation.docs = []
    fake_db.vehicle_costs.docs = []
    service = build_service(monkeypatch, fake_db)

    result = run(service.find_inconsistencies())

    assert result == {"orphan_expenses": [], "orphan_links": []}


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
