"""
Verifica export_service.export_commissions: le provvigioni inserite
manualmente sono provvigioni vere a tutti gli effetti (vedi
commission_service.normalize_manual_commission) e devono comparire
nell'export CSV insieme a quelle calcolate dagli ordini, marcate nella
colonna "origine".

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_export_service_commissions.py -v
"""
import sys
import asyncio
import csv
import io

sys.path.insert(0, ".")

import services.export_service as export_mod
from services.export_service import ExportService


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
        return FakeCursor([d for d in self._docs if d.get("user_id") == query.get("user_id")])


class FakeDb:
    def __init__(self, collections):
        self._collections = collections

    def __getattr__(self, name):
        return FakeCollection(self._collections.get(name, []))


USER = {"id": "user-1"}

REAL_COMMISSION = {
    "id": "c-1", "user_id": "user-1", "period": "2026-08", "client_id": "cl-1",
    "mandante_id": "m-1", "amount": 100, "rate": 10, "status": "maturato",
}
MANUAL_COMMISSION = {
    "user_id": "user-1", "period": "2026-08", "amount": 250,
    "client_id": None, "mandante_id": "m-1", "stato": "incassato",
}
CLIENTS = [{"id": "cl-1", "user_id": "user-1", "company_name": "Bar Rossi"}]
MANDANTI = [{"id": "m-1", "user_id": "user-1", "name": "Azienda A"}]


async def _allow_always(*a, **kw):
    return True


def build_service(monkeypatch, commissions=None, manual_commissions=None):
    fake_db = FakeDb({
        "commissions": commissions or [],
        "manual_commissions": manual_commissions or [],
        "clients": CLIENTS,
        "mandanti": MANDANTI,
    })
    monkeypatch.setattr(export_mod, "db", fake_db)
    monkeypatch.setattr(export_mod, "check_and_record", _allow_always)
    return ExportService()


async def _collect_csv_rows(response):
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, str) else chunk.decode("utf-8"))
    text = "".join(chunks).lstrip("﻿")
    return list(csv.DictReader(io.StringIO(text), delimiter=";"))


def test_export_include_provvigioni_reali_e_manuali(monkeypatch):
    service = build_service(monkeypatch, commissions=[REAL_COMMISSION], manual_commissions=[MANUAL_COMMISSION])
    response = run(service.export_commissions(USER))
    rows = run(_collect_csv_rows(response))
    assert len(rows) == 2
    origini = {r["origine"] for r in rows}
    assert origini == {"ordine", "manuale"}


def test_export_provvigione_manuale_ha_client_mandante_risolti(monkeypatch):
    service = build_service(monkeypatch, manual_commissions=[MANUAL_COMMISSION])
    response = run(service.export_commissions(USER))
    rows = run(_collect_csv_rows(response))
    assert len(rows) == 1
    row = rows[0]
    assert row["origine"] == "manuale"
    assert row["mandante"] == "Azienda A"
    assert row["client"] == ""  # nessun client_id sulla manuale di test
    assert row["status"] == "incassato"
    assert row["amount"] == "250"
    assert row["rate"] == ""


def test_export_senza_provvigioni_manuali_non_rompe(monkeypatch):
    service = build_service(monkeypatch, commissions=[REAL_COMMISSION])
    response = run(service.export_commissions(USER))
    rows = run(_collect_csv_rows(response))
    assert len(rows) == 1
    assert rows[0]["origine"] == "ordine"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
