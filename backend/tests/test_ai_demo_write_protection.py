"""
Verifica che un account demo non possa scrivere sul CRM tramite /api/ai/chat.

Prima della fix, il ciclo dei tool dentro AiService.chat() chiamava
execute_crm_tool() direttamente per qualunque tool che non richiedesse
conferma (add_client, add_appointment, add_lead, add_note_to_client, e
add_expense sotto soglia), senza controllare user["is_demo"]. La protezione
esisteva solo su /execute-action, /cancel-action e DELETE /history.

Questo test invoca AiService.chat() con un utente demo, mockando l'SDK
Anthropic in modo che il modello richieda il tool "add_client" (nessuna
conferma richiesta), e verifica che:
  1. execute_crm_tool NON venga mai chiamato per l'utente demo.
  2. Il risultato mostrato all'utente sia il messaggio di blocco.
  3. Il log dell'azione venga comunque registrato con stato "fallita".
"""
import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, ".")

from services.ai_service import AiService, CRM_WRITE_TOOLS


def _make_tool_use_message(tool_name="add_client", tool_input=None):
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input or {"name": "Mario Rossi", "phone": "3331234567"}
    block.id = "toolu_test123"

    message = MagicMock()
    message.stop_reason = "tool_use"
    message.content = [block]
    return message


def _make_final_message(text="Fatto."):
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    message = MagicMock()
    message.stop_reason = "end_turn"
    message.content = [text_block]
    return message


class FakePayload:
    message = "Aggiungi il cliente Mario Rossi"
    channel = "chat"


def test_demo_user_cannot_write_via_chat_tool_loop(monkeypatch):
    service = AiService.__new__(AiService)  # skip __init__ (repo wiring)
    service.repo = MagicMock()
    service.repo.find_recent_for_context = AsyncMock(return_value=[])
    service.repo.insert_log = AsyncMock(return_value=None)

    monkeypatch.setattr(service, "gather_context", AsyncMock(return_value="(contesto vuoto)"))
    monkeypatch.setattr(service, "requires_confirmation", lambda name, inp: False)
    monkeypatch.setattr(service, "_log_action", AsyncMock(return_value={"id": "log_1"}))

    execute_crm_tool_mock = AsyncMock(return_value="✅ Cliente aggiunto")
    monkeypatch.setattr(service, "execute_crm_tool", execute_crm_tool_mock)

    tool_use_msg = _make_tool_use_message("add_client")
    final_msg = _make_final_message("Nell'account demo non posso farlo, ma posso mostrarti come funziona.")

    fake_anthropic_client = MagicMock()
    fake_anthropic_client.messages.create.side_effect = [tool_use_msg, final_msg]

    fake_anthropic_module = types.SimpleNamespace(
        Anthropic=MagicMock(return_value=fake_anthropic_client)
    )
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic_module)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-dummy")

    demo_user = {"id": "demo_user_1", "is_demo": True, "role": "user"}

    result = asyncio.get_event_loop().run_until_complete(
        service.chat(demo_user, FakePayload())
    )

    # 1. Il tool CRM reale non deve MAI essere eseguito per l'utente demo.
    execute_crm_tool_mock.assert_not_called()

    # 2. Il log dell'azione deve comunque registrare il tentativo bloccato.
    logged_calls = service._log_action.call_args_list
    assert len(logged_calls) == 1
    _, kwargs = logged_calls[0]
    assert kwargs.get("status") == "fallita"
    assert "non modificare i dati" in kwargs.get("result", "")

    # 3. add_client fa parte dei tool protetti.
    assert "add_client" in CRM_WRITE_TOOLS

    print("OK: account demo bloccato correttamente nel ciclo tool della chat")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
