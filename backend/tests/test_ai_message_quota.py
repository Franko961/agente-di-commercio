"""
Test per il limite mensile di messaggi AI del piano Base (100/mese, vedi
core/config.py PLANS['base']['ai_monthly_message_limit']).

Prima di questa modifica il limite era solo testo descrittivo nella pagina
prezzi: nessuna parte del backend contava o bloccava davvero i messaggi.
Verifica che AiService._enforce_ai_message_quota():
  1. blocchi (HTTP 402) un utente 'base' che ha già raggiunto il limite;
  2. lasci passare un utente 'base' sotto al limite;
  3. non applichi mai un limite a un utente 'pro' (ai_monthly_message_limit None);
  4. non applichi mai un limite a un admin, indipendentemente dal piano.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest tests/test_ai_message_quota.py -v
"""
import sys
import asyncio

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

from tests.test_ai_tool_forcing import (
    build_service,
    install_fake_anthropic,
    make_message,
    make_text_block,
    Payload,
)
from core.config import PLANS


def run(coro):
    return asyncio.run(coro)


def test_utente_base_bloccato_al_limite():
    service, _ = build_service()
    service.repo.message_count_this_month = PLANS["base"]["ai_monthly_message_limit"]

    with pytest.raises(HTTPException) as exc_info:
        run(service.chat({"id": "user-1", "plan": "base"}, Payload("ciao")))

    assert exc_info.value.status_code == 402
    assert "100 messaggi" in exc_info.value.detail


def test_utente_base_sotto_al_limite_passa():
    service, _ = build_service()
    service.repo.message_count_this_month = PLANS["base"]["ai_monthly_message_limit"] - 1

    install_fake_anthropic({"responses": [
        make_message([make_text_block("Ciao! Come posso aiutarti?")], stop_reason="end_turn"),
    ]})

    result = run(service.chat({"id": "user-1", "plan": "base"}, Payload("ciao")))
    assert result["response"] == "Ciao! Come posso aiutarti?"


def test_utente_pro_senza_limite():
    service, _ = build_service()
    # Molto oltre qualunque limite Base plausibile: un piano Pro non deve
    # comunque mai essere bloccato (ai_monthly_message_limit è None).
    service.repo.message_count_this_month = 100_000

    install_fake_anthropic({"responses": [
        make_message([make_text_block("Fatto.")], stop_reason="end_turn"),
    ]})

    result = run(service.chat({"id": "user-1", "plan": "pro"}, Payload("ciao")))
    assert result["response"] == "Fatto."


def test_admin_non_soggetto_al_limite():
    service, _ = build_service()
    service.repo.message_count_this_month = 100_000

    install_fake_anthropic({"responses": [
        make_message([make_text_block("Fatto.")], stop_reason="end_turn"),
    ]})

    result = run(service.chat({"id": "admin-1", "plan": "base", "role": "admin"}, Payload("ciao")))
    assert result["response"] == "Fatto."


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
