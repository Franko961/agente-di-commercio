"""
Verifica il fix della confusione di tipo tra JWT (core/security.py):
get_current_user() ora rifiuta qualunque token che non porti
"type": "access", non solo quelli scaduti o con firma non valida.

Prima di questo fix, un token con uno scopo diverso ma firmato con lo
stesso JWT_SECRET — in particolare quello emesso da
create_document_download_token, pensato per finire in un URL (link di
download, quindi esposto a cronologia browser/log/analytics) e valere
SOLO per un documento specifico per pochi minuti — veniva comunque
accettato da get_current_user come una sessione completa, perché
quest'ultima leggeva solo "sub" senza controllare "type"/"purpose".

Esegui con:
    JWT_SECRET=test python -m pytest tests/test_jwt_type_confusion.py -v
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

import core.security as security_mod
from core.config import JWT_ALG, JWT_SECRET
from core.security import (
    create_access_token,
    create_document_download_token,
    create_impersonation_token,
    get_current_user,
)
from tests.test_impersonation import FakeDb, FakeRequest


def run(coro):
    return asyncio.run(coro)


USER_DOC = {
    "id": "user-1",
    "email": "utente@esempio.it",
    "role": "agent",
    "subscription_status": "active",
}


def test_access_token_normale_viene_accettato(monkeypatch):
    monkeypatch.setattr(security_mod, "db", FakeDb(USER_DOC))
    token = create_access_token("user-1", "utente@esempio.it")

    result = run(get_current_user(FakeRequest(token)))

    assert result["id"] == "user-1"


def test_token_impersonificazione_viene_accettato(monkeypatch):
    """Controllo di non-regressione: create_impersonation_token porta
    già "type": "access" (deve continuare a funzionare come sessione)."""
    monkeypatch.setattr(security_mod, "db", FakeDb(USER_DOC))
    token = create_impersonation_token("admin-1", "user-1", "utente@esempio.it")

    result = run(get_current_user(FakeRequest(token)))

    assert result["id"] == "user-1"


def test_token_download_documento_viene_rifiutato_come_sessione(monkeypatch):
    """Il caso centrale del fix: un token emesso per scaricare UN documento
    specifico non deve autenticare come sessione completa su nessun altro
    endpoint, anche se firmato correttamente e non scaduto."""
    monkeypatch.setattr(security_mod, "db", FakeDb(USER_DOC))
    token = create_document_download_token("user-1", "doc-1")

    with pytest.raises(HTTPException) as exc_info:
        run(get_current_user(FakeRequest(token)))

    assert exc_info.value.status_code == 401


def test_token_senza_claim_type_viene_rifiutato(monkeypatch):
    """Qualunque JWT futuro firmato con lo stesso segreto ma senza
    "type": "access" (per uno scopo diverso da una sessione) deve essere
    rifiutato di default, non solo il caso specifico del download."""
    monkeypatch.setattr(security_mod, "db", FakeDb(USER_DOC))
    payload = {
        "sub": "user-1",
        "purpose": "qualcosa_altro",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

    with pytest.raises(HTTPException) as exc_info:
        run(get_current_user(FakeRequest(token)))

    assert exc_info.value.status_code == 401


def test_token_con_type_diverso_da_access_viene_rifiutato(monkeypatch):
    monkeypatch.setattr(security_mod, "db", FakeDb(USER_DOC))
    payload = {
        "sub": "user-1",
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

    with pytest.raises(HTTPException) as exc_info:
        run(get_current_user(FakeRequest(token)))

    assert exc_info.value.status_code == 401


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
