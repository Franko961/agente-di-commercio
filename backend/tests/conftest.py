import sys
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, ".")

import services.ai_service as ai_service_mod
import services.email_service as email_service_mod
import services.google_calendar_service as gcal_service_mod


@pytest.fixture(autouse=True)
def _no_real_telemetry_writes(monkeypatch):
    """I test unitari di questo progetto non hanno un MongoDB reale a
    disposizione (usano repository finti in memoria). La telemetria
    aggiunta in core/observability.py (record_event/record_api_call) scrive
    invece sempre sul vero `db` importato da core.database — senza questo
    fixture, qualunque test che esercita un percorso instrumentato (chat
    AI, invio email, sync Google Calendar) tenterebbe una vera connessione
    a MongoDB, con conseguente rallentamento/timeout.

    autouse=True: si applica a TUTTI i test senza doverlo richiamare
    esplicitamente in ciascuno — compreso ogni nuovo test aggiunto in
    futuro che eserciti uno di questi percorsi.

    Nota: va patchato il nome importato in ciascun modulo chiamante (es.
    services.ai_service.record_event), non l'originale in
    core.observability — 'from X import Y' copia il riferimento al momento
    dell'import, patchare l'originale dopo non lo aggiorna nei moduli che
    l'hanno già importato."""
    monkeypatch.setattr(ai_service_mod, "record_event", AsyncMock())
    monkeypatch.setattr(email_service_mod, "record_event", AsyncMock())
    monkeypatch.setattr(gcal_service_mod, "record_event", AsyncMock())
