"""
Verifica ClientService.get_client: le provvigioni inserite manualmente con
client_id valorizzato su questo cliente contano come vere anche nel
dettaglio cliente (fatturato/provvigioni cliente in ClientDetail.jsx), non
solo nella pagina Provvigioni — vedi commission_service.normalize_manual_commission.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_client_service_manual_commissions.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

import services.client_service as client_service_mod
from services.client_service import ClientService


def run(coro):
    return asyncio.run(coro)


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, n):
        return self._docs[:n]


class FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, query, projection=None):
        matched = [
            d for d in self._docs if all(d.get(k) == v for k, v in query.items())
        ]
        return FakeCursor(matched)


class FakeDb:
    def __init__(self, collections):
        self._collections = collections

    def __getattr__(self, name):
        return FakeCollection(self._collections.get(name, []))


class FakeClientRepo:
    def __init__(self, client):
        self.client = client

    async def find_one(self, cid, user_id):
        return dict(self.client) if self.client and self.client["id"] == cid else None


USER = {"id": "user-1"}
CLIENT = {"id": "cl-1", "user_id": "user-1", "company_name": "Bar Rossi"}

REAL_COMMISSION = {
    "id": "c-1",
    "user_id": "user-1",
    "client_id": "cl-1",
    "period": "2026-08",
    "amount": 100,
    "rate": 10,
    "status": "maturato",
}
MANUAL_FOR_CLIENT = {
    "user_id": "user-1",
    "client_id": "cl-1",
    "period": "2026-08",
    "amount": 250,
    "stato": "incassato",
}
MANUAL_OTHER_CLIENT = {
    "user_id": "user-1",
    "client_id": "cl-2",
    "period": "2026-08",
    "amount": 999,
    "stato": "maturato",
}


def build_service(monkeypatch, commissions=None, manual_commissions=None):
    fake_db = FakeDb(
        {
            "offers": [],
            "appointments": [],
            "documents": [],
            "commissions": commissions or [],
            "manual_commissions": manual_commissions or [],
        }
    )
    monkeypatch.setattr(client_service_mod, "db", fake_db)
    return ClientService(repo=FakeClientRepo(CLIENT))


def test_include_provvigioni_manuali_del_cliente(monkeypatch):
    service = build_service(
        monkeypatch,
        commissions=[REAL_COMMISSION],
        manual_commissions=[MANUAL_FOR_CLIENT, MANUAL_OTHER_CLIENT],
    )
    result = run(service.get_client(USER, "cl-1"))
    assert (
        len(result["commissions"]) == 2
    )  # reale + manuale di questo cliente, non quella di cl-2
    amounts = {cm["amount"] for cm in result["commissions"]}
    assert amounts == {100, 250}


def test_provvigione_manuale_normalizzata_ha_source_manual(monkeypatch):
    service = build_service(monkeypatch, manual_commissions=[MANUAL_FOR_CLIENT])
    result = run(service.get_client(USER, "cl-1"))
    assert result["commissions"][0]["source"] == "manual"
    assert result["commissions"][0]["status"] == "incassato"


def test_provvigione_reale_taggata_source_order(monkeypatch):
    service = build_service(monkeypatch, commissions=[REAL_COMMISSION])
    result = run(service.get_client(USER, "cl-1"))
    assert result["commissions"][0]["source"] == "order"


def test_senza_provvigioni_manuali_non_rompe(monkeypatch):
    service = build_service(monkeypatch, commissions=[REAL_COMMISSION])
    result = run(service.get_client(USER, "cl-1"))
    assert len(result["commissions"]) == 1


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
