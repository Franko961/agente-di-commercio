"""
Verifica services.transcription_service: trascrizione vocale (Whisper) usata
al posto del riconoscimento vocale nativo del browser, che Safari/WebKit non
implementa affatto (assente su ogni browser su iPhone) — segnalato da Franco
il 2026-09-14 ("abbiamo scritto sulla home che si registrano anche note
vocalmente, abbiamo realmente questa funzione?").

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_ai_transcription.py -v
"""

import asyncio
import sys

import pytest
import requests as real_requests
from fastapi import HTTPException

sys.path.insert(0, ".")

import services.transcription_service as transcription_mod
from services.transcription_service import (
    MAX_AUDIO_BYTES,
    transcribe_audio,
    transcribe_upload,
)


def run(coro):
    return asyncio.run(coro)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json


class FakeRequests:
    # transcribe_audio fa "except requests.RequestException" sul nome
    # `requests` così com'è nel suo modulo — dopo il monkeypatch quel nome
    # punta a un'istanza di questa classe, quindi deve esporre lei stessa
    # l'eccezione reale perché quella riga continui a risolversi.
    RequestException = real_requests.RequestException

    def __init__(self, response=None, raise_exc=None):
        self.response = response or FakeResponse(200, {"text": "Aggiungi una nota"})
        self.raise_exc = raise_exc
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.raise_exc:
            raise self.raise_exc
        return self.response


class FakeUploadFile:
    """Riproduce solo l'interfaccia usata da transcribe_upload
    (file.read(n) e file.filename) — non il vero starlette.UploadFile."""

    def __init__(self, chunks, filename="voice.webm"):
        self._chunks = list(chunks)
        self.filename = filename

    async def read(self, n):
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


async def _always_allowed(kind, key, max_attempts, window_minutes):
    return True


async def _always_blocked(kind, key, max_attempts, window_minutes):
    return False


def test_transcribe_audio_ritorna_il_testo(monkeypatch):
    fake = FakeRequests(FakeResponse(200, {"text": "Aggiungi Rossi Spa"}))
    monkeypatch.setattr(transcription_mod, "requests", fake)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    result = run(transcribe_audio(b"audio-bytes", "voice.webm"))

    assert result == "Aggiungi Rossi Spa"
    # Verifica che la chiamata sia fatta con lingua italiana e il modello giusto.
    _, kwargs = fake.calls[0]
    assert kwargs["data"]["language"] == "it"
    assert kwargs["data"]["model"] == "whisper-1"


def test_transcribe_audio_senza_chiave_solleva_500(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        run(transcribe_audio(b"audio-bytes", "voice.webm"))
    assert exc_info.value.status_code == 500


def test_transcribe_audio_testo_vuoto_solleva_400(monkeypatch):
    fake = FakeRequests(FakeResponse(200, {"text": "   "}))
    monkeypatch.setattr(transcription_mod, "requests", fake)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with pytest.raises(HTTPException) as exc_info:
        run(transcribe_audio(b"audio-bytes", "voice.webm"))
    assert exc_info.value.status_code == 400


def test_transcribe_audio_errore_http_solleva_502(monkeypatch):
    fake = FakeRequests(FakeResponse(500, {}))
    monkeypatch.setattr(transcription_mod, "requests", fake)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with pytest.raises(HTTPException) as exc_info:
        run(transcribe_audio(b"audio-bytes", "voice.webm"))
    assert exc_info.value.status_code == 502


def test_transcribe_audio_rete_irraggiungibile_solleva_502(monkeypatch):
    fake = FakeRequests(raise_exc=real_requests.ConnectionError("no network"))
    monkeypatch.setattr(transcription_mod, "requests", fake)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with pytest.raises(HTTPException) as exc_info:
        run(transcribe_audio(b"audio-bytes", "voice.webm"))
    assert exc_info.value.status_code == 502


def test_transcribe_upload_riuscito(monkeypatch):
    fake = FakeRequests(FakeResponse(200, {"text": "Nota registrata"}))
    monkeypatch.setattr(transcription_mod, "requests", fake)
    monkeypatch.setattr(transcription_mod, "check_and_record", _always_allowed)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    upload = FakeUploadFile([b"abc", b"def"])
    result = run(transcribe_upload(upload, "user-1"))

    assert result == "Nota registrata"


def test_transcribe_upload_oltre_il_limite_solleva_413(monkeypatch):
    monkeypatch.setattr(transcription_mod, "check_and_record", _always_allowed)
    # Un solo chunk più grande del limite, seguito da fine stream.
    upload = FakeUploadFile([b"x" * (MAX_AUDIO_BYTES + 1)])

    with pytest.raises(HTTPException) as exc_info:
        run(transcribe_upload(upload, "user-1"))
    assert exc_info.value.status_code == 413


def test_transcribe_upload_vuoto_solleva_400(monkeypatch):
    monkeypatch.setattr(transcription_mod, "check_and_record", _always_allowed)
    upload = FakeUploadFile([])

    with pytest.raises(HTTPException) as exc_info:
        run(transcribe_upload(upload, "user-1"))
    assert exc_info.value.status_code == 400


def test_transcribe_upload_rate_limit_solleva_429(monkeypatch):
    monkeypatch.setattr(transcription_mod, "check_and_record", _always_blocked)
    upload = FakeUploadFile([b"abc"])

    with pytest.raises(HTTPException) as exc_info:
        run(transcribe_upload(upload, "user-1"))
    assert exc_info.value.status_code == 429


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
