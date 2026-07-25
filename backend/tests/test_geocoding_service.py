"""
Test per geocoding_service: la ricerca indirizzo->coordinate usata come
alternativa all'inserimento manuale di latitudine/longitudine nel form
cliente. Nominatim viene mockato (nessuna chiamata di rete reale nei test).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_geocoding_service.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

import services.geocoding_service as geocoding_mod
from services.geocoding_service import GeocodingService
from fastapi import HTTPException


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


async def _allow_always(*a, **kw):
    return True


async def _deny_always(*a, **kw):
    return False


def test_ricerca_restituisce_coordinate(monkeypatch):
    monkeypatch.setattr(geocoding_mod, "check_and_record", _allow_always)
    fake_payload = [
        {"display_name": "Via Roma 1, Bologna, Italia", "lat": "44.4938", "lon": "11.3387"},
    ]
    monkeypatch.setattr(geocoding_mod.requests, "get", lambda *a, **kw: FakeResponse(fake_payload))

    service = GeocodingService()
    results = run(service.search_address("u1", "Via Roma 1, Bologna"))

    assert len(results) == 1
    assert results[0]["lat"] == 44.4938
    assert results[0]["lng"] == 11.3387
    assert "Bologna" in results[0]["display_name"]


def test_nessun_risultato_restituisce_lista_vuota(monkeypatch):
    monkeypatch.setattr(geocoding_mod, "check_and_record", _allow_always)
    monkeypatch.setattr(geocoding_mod.requests, "get", lambda *a, **kw: FakeResponse([]))

    service = GeocodingService()
    results = run(service.search_address("u1", "indirizzo inesistente xyz"))

    assert results == []


def test_query_troppo_corta_rifiutata(monkeypatch):
    monkeypatch.setattr(geocoding_mod, "check_and_record", _allow_always)
    service = GeocodingService()
    try:
        run(service.search_address("u1", "ab"))
        assert False, "doveva sollevare HTTPException"
    except HTTPException as e:
        assert e.status_code == 400


def test_rate_limit_superato_restituisce_429(monkeypatch):
    monkeypatch.setattr(geocoding_mod, "check_and_record", _deny_always)
    service = GeocodingService()
    try:
        run(service.search_address("u1", "Via Roma 1, Bologna"))
        assert False, "doveva sollevare HTTPException"
    except HTTPException as e:
        assert e.status_code == 429


def test_errore_di_rete_restituisce_502(monkeypatch):
    monkeypatch.setattr(geocoding_mod, "check_and_record", _allow_always)

    def _raise(*a, **kw):
        raise geocoding_mod.requests.RequestException("timeout")
    monkeypatch.setattr(geocoding_mod.requests, "get", _raise)

    service = GeocodingService()
    try:
        run(service.search_address("u1", "Via Roma 1, Bologna"))
        assert False, "doveva sollevare HTTPException"
    except HTTPException as e:
        assert e.status_code == 502
