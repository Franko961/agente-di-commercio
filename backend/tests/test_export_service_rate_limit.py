"""
Verifica il rate limit sugli export CSV standard (clienti, offerte,
provvigioni, lead): ognuno legge fino a 5000 documenti su una o più
collection, ma prima di questa modifica non aveva alcun limite di
frequenza, a differenza dell'export equivalente lato GDPR
(services/gdpr_service.py) che è già protetto.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_export_service_rate_limit.py -v
"""
import sys
import asyncio

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

import services.export_service as export_mod
from services.export_service import ExportService


def run(coro):
    return asyncio.run(coro)


async def _allow_always(*a, **kw):
    return True


async def _deny_always(*a, **kw):
    return False


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, n):
        return self._docs[:n]


class FakeCollection:
    def find(self, query, projection=None):
        return FakeCursor([])


class FakeDb:
    def __getattr__(self, name):
        return FakeCollection()


USER = {"id": "user-1"}


def test_export_permesso_normalmente(monkeypatch):
    monkeypatch.setattr(export_mod, "db", FakeDb())
    monkeypatch.setattr(export_mod, "check_and_record", _allow_always)

    service = ExportService()
    response = run(service.export_clients(USER))

    assert response.status_code == 200


@pytest.mark.parametrize("method_name", [
    "export_clients", "export_offers", "export_commissions", "export_leads",
])
def test_export_bloccato_da_troppe_richieste(monkeypatch, method_name):
    monkeypatch.setattr(export_mod, "db", FakeDb())
    monkeypatch.setattr(export_mod, "check_and_record", _deny_always)

    service = ExportService()
    method = getattr(service, method_name)

    with pytest.raises(HTTPException) as exc_info:
        run(method(USER))

    assert exc_info.value.status_code == 429


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
