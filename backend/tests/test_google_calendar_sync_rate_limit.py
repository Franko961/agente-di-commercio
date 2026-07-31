"""
Verifica il rate limit su GoogleCalendarService.sync_now(): il trigger
manuale di sincronizzazione (oltre al polling periodico già in background)
non aveva alcun limite di frequenza, permettendo di generare traffico
eccessivo verso le API Google Calendar o forzare refresh di token non
necessari — stessa protezione già applicata alle altre integrazioni esterne
a consumo (geocoding, route planning).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_google_calendar_sync_rate_limit.py -v
"""
import sys
import asyncio

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

import services.google_calendar_service as gcal_mod
from services.google_calendar_service import GoogleCalendarService


def run(coro):
    return asyncio.run(coro)


async def _allow_always(*a, **kw):
    return True


async def _deny_always(*a, **kw):
    return False


class FakeRepo:
    def __init__(self):
        self.find_by_user_calls = 0

    async def find_by_user(self, user_id):
        self.find_by_user_calls += 1
        return None


def test_sync_now_permesso_normalmente(monkeypatch):
    monkeypatch.setattr(gcal_mod, "check_and_record", _allow_always)
    repo = FakeRepo()
    service = GoogleCalendarService(repo=repo)

    run(service.sync_now("user-1"))

    assert repo.find_by_user_calls == 1


def test_sync_now_bloccato_da_troppe_richieste(monkeypatch):
    monkeypatch.setattr(gcal_mod, "check_and_record", _deny_always)
    repo = FakeRepo()
    service = GoogleCalendarService(repo=repo)

    with pytest.raises(HTTPException) as exc_info:
        run(service.sync_now("user-1"))

    assert exc_info.value.status_code == 429
    # Bloccato PRIMA di toccare la connessione: nessuna chiamata sprecata.
    assert repo.find_by_user_calls == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
