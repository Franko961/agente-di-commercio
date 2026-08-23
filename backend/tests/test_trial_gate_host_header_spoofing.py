"""
Verifica che il gate trial/abbonamento scaduto (core/security.py,
get_current_user) decida l'esenzione in base al path ASGI reale
(request.scope["path"]), non a request.url.path — che starlette ricostruisce
concatenando l'header Host col path (vulnerabile a manipolazione: CVE
PYSEC-2026-161/248, "Host header path confusion" in starlette < 1.0.1/1.3.0).

Se il gate usasse request.url.path, un Host header malformato potrebbe far
percepire come esente (es. "/api/subscription...") una richiesta il cui path
reale è un endpoint qualunque, bypassando il blocco 402 per trial scaduto.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_trial_gate_host_header_spoofing.py -v
"""
import sys
import asyncio

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

from core.security import create_access_token, get_current_user
import core.security as security_mod
from tests.test_impersonation import FakeDb


def run(coro):
    return asyncio.run(coro)


class SpoofedRequest:
    """Simula un Host header malformato: request.url.path (come lo
    ricostruirebbe starlette) dichiara un prefisso esente, ma il path ASGI
    realmente instradato (scope["path"]) è un endpoint normale."""

    def __init__(self, token, spoofed_url_path, real_scope_path):
        self.cookies = {"access_token": token}
        self.headers = {}
        self.url = type("U", (), {"path": spoofed_url_path})()
        self.scope = {"path": real_scope_path}


def test_gate_trial_usa_il_path_reale_non_quello_ricostruito_da_host_spoofato(monkeypatch):
    user_doc = {
        "id": "user-42", "email": "utente@esempio.it", "role": "agent",
        "subscription_status": "cancelled",
    }
    monkeypatch.setattr(security_mod, "db", FakeDb(user_doc))
    token = create_access_token("user-42", "utente@esempio.it")

    request = SpoofedRequest(token, spoofed_url_path="/api/subscription/status", real_scope_path="/api/clients")

    with pytest.raises(HTTPException) as exc_info:
        run(get_current_user(request))
    assert exc_info.value.status_code == 402


def test_gate_trial_esenta_correttamente_quando_il_path_reale_e_esente(monkeypatch):
    user_doc = {
        "id": "user-42", "email": "utente@esempio.it", "role": "agent",
        "subscription_status": "cancelled",
    }
    monkeypatch.setattr(security_mod, "db", FakeDb(user_doc))
    token = create_access_token("user-42", "utente@esempio.it")

    request = SpoofedRequest(token, spoofed_url_path="/api/clients", real_scope_path="/api/subscription/status")

    result = run(get_current_user(request))
    assert result["id"] == "user-42"
