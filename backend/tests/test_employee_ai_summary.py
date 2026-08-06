"""
Verifica services/ai_service.generate_employee_summary(): riepilogo in
linguaggio naturale del dipendente per la scheda Personale, stessa forma
minimale di suggestions() (nessuna cronologia, nessun tool). Mock completo
dell'SDK Anthropic — nessuna vera chiamata API, nessun DB reale (stesso
pattern di test_ai_tool_forcing.py).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_employee_ai_summary.py -v
"""
import sys
import types
import asyncio
from types import SimpleNamespace

import pytest

sys.path.insert(0, ".")

import services.ai_service as ai_service_mod


def run(coro):
    return asyncio.run(coro)


def make_text_message(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


class FakeMessages:
    def __init__(self, responses=None, raise_error=None):
        self._responses = list(responses or [])
        self.raise_error = raise_error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_error:
            raise self.raise_error
        return self._responses.pop(0)


class FakeAnthropicClient:
    def __init__(self, messages):
        self.messages = messages


def install_fake_anthropic(messages_holder):
    fake_module = types.ModuleType("anthropic")

    def _Anthropic(api_key=None):
        return FakeAnthropicClient(messages_holder["messages"])

    fake_module.Anthropic = _Anthropic
    sys.modules["anthropic"] = fake_module
    return fake_module


EMPLOYEE = {"id": "emp-1", "name": "Mario", "surname": "Rossi", "role": "Autista", "employment_status": "attivo"}
SUMMARY = {
    "ferie": {"spettanti": 26, "godute": 5, "residue": 21},
    "permessi": {"ore_richieste": 4, "ore_approvate": 4},
    "malattie": {"giorni": 3, "richieste": []},
    "kpi": {"presenze_stimate": 150, "assenze_giorni": 8, "ferie_giorni": 5, "permessi_ore": 4, "malattie_giorni": 3},
    "current_status": None,
}


def test_generate_employee_summary_senza_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = run(ai_service_mod.ai_service.generate_employee_summary(EMPLOYEE, SUMMARY))
    assert result == {"summary": None}


def test_generate_employee_summary_happy_path(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    messages = FakeMessages(responses=[make_text_message("Mario ha 3 giorni di malattia quest'anno, ferie quasi esaurite.")])
    install_fake_anthropic({"messages": messages})

    result = run(ai_service_mod.ai_service.generate_employee_summary(EMPLOYEE, SUMMARY))

    assert result == {"summary": "Mario ha 3 giorni di malattia quest'anno, ferie quasi esaurite."}
    assert len(messages.calls) == 1


def test_generate_employee_summary_include_nome_e_numeri_nel_prompt(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    messages = FakeMessages(responses=[make_text_message("ok")])
    install_fake_anthropic({"messages": messages})

    run(ai_service_mod.ai_service.generate_employee_summary(EMPLOYEE, SUMMARY))

    prompt = messages.calls[0]["messages"][0]["content"]
    assert "Mario Rossi" in prompt
    assert "21" in prompt  # ferie residue
    assert "3" in prompt   # giorni malattia


def test_generate_employee_summary_non_menziona_diagnosi_nel_system_prompt(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    messages = FakeMessages(responses=[make_text_message("ok")])
    install_fake_anthropic({"messages": messages})

    run(ai_service_mod.ai_service.generate_employee_summary(EMPLOYEE, SUMMARY))

    system_prompt = messages.calls[0]["system"]
    assert "diagnosi" in system_prompt.lower() or "sanitari" in system_prompt.lower()


def test_generate_employee_summary_gestisce_errori_dell_api(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    messages = FakeMessages(raise_error=RuntimeError("API down"))
    install_fake_anthropic({"messages": messages})

    result = run(ai_service_mod.ai_service.generate_employee_summary(EMPLOYEE, SUMMARY))

    assert result == {"summary": None}
