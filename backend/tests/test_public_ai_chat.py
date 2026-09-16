"""
Test per services.public_ai_chat_service (chat AI pubblica sulla homepage,
senza autenticazione, non collegata al CRM di nessun utente).

Verifica: rate limit per IP, nessun tool esposto al modello, prezzi/feature
nel system prompt letti da core.config.PLANS (mai un numero scritto a mano
nel test — se PLANS cambia, il test deve restare valido), log anonimo delle
conversazioni (nessun IP salvato nel documento).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest tests/test_public_ai_chat.py -v
"""

import asyncio
import sys
import types
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

from core.config import PLANS, TRIAL_DAYS


def run(coro):
    return asyncio.run(coro)


def make_text_message(text):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5, server_tool_use=None),
    )


class FakeMessages:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class FakeAnthropicClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)


def install_fake_anthropic(response, created_clients=None):
    fake_module = types.ModuleType("anthropic")

    def _Anthropic(api_key=None):
        client = FakeAnthropicClient(response)
        if created_clients is not None:
            created_clients.append(client)
        return client

    fake_module.Anthropic = _Anthropic
    sys.modules["anthropic"] = fake_module


class FakeLogRepo:
    def __init__(self):
        self.docs = []

    async def insert(self, doc):
        self.docs.append(doc)
        return doc


async def _allow(*a, **k):
    return True


async def _deny(*a, **k):
    return False


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


def test_chat_risponde_e_logga_in_forma_anonima(monkeypatch):
    import services.public_ai_chat_service as svc

    install_fake_anthropic(make_text_message("Il piano Base costa questo."))
    monkeypatch.setattr(svc, "check_and_record", _allow)
    fake_log = FakeLogRepo()
    monkeypatch.setattr(svc, "public_ai_chat_log_repository", fake_log)

    result = run(svc.chat("quanto costa?", [], "1.2.3.4"))

    assert result == "Il piano Base costa questo."
    assert len(fake_log.docs) == 1
    logged = fake_log.docs[0]
    assert logged["domanda"] == "quanto costa?"
    assert logged["risposta"] == "Il piano Base costa questo."
    # Nessun IP né altro identificativo nel documento salvato.
    assert "ip" not in logged and "ip_address" not in logged
    assert set(logged.keys()) == {"id", "domanda", "risposta", "created_at"}


def test_rate_limit_supera_il_massimo_solleva_429(monkeypatch):
    import services.public_ai_chat_service as svc

    install_fake_anthropic(make_text_message("risposta"))
    monkeypatch.setattr(svc, "check_and_record", _deny)
    monkeypatch.setattr(svc, "public_ai_chat_log_repository", FakeLogRepo())

    with pytest.raises(HTTPException) as exc_info:
        run(svc.chat("ciao", [], "1.2.3.4"))

    assert exc_info.value.status_code == 429


def test_nessun_tool_esposto_al_modello(monkeypatch):
    import services.public_ai_chat_service as svc

    created_clients = []
    install_fake_anthropic(make_text_message("risposta"), created_clients)
    monkeypatch.setattr(svc, "check_and_record", _allow)
    monkeypatch.setattr(svc, "public_ai_chat_log_repository", FakeLogRepo())

    run(svc.chat("ciao", [], "1.2.3.4"))

    assert len(created_clients) == 1
    call_kwargs = created_clients[0].messages.calls[0]
    assert "tools" not in call_kwargs
    assert call_kwargs["max_tokens"] == svc.PUBLIC_CHAT_MAX_TOKENS


def test_system_prompt_contiene_prezzi_reali_da_plans(monkeypatch):
    import services.public_ai_chat_service as svc

    created_clients = []
    install_fake_anthropic(make_text_message("risposta"), created_clients)
    monkeypatch.setattr(svc, "check_and_record", _allow)
    monkeypatch.setattr(svc, "public_ai_chat_log_repository", FakeLogRepo())

    run(svc.chat("quanto costa?", [], "1.2.3.4"))

    system_prompt = created_clients[0].messages.calls[0]["system"]
    assert f"€{PLANS['base']['price_eur']}" in system_prompt
    assert f"€{PLANS['pro']['price_eur']}" in system_prompt
    assert str(TRIAL_DAYS) in system_prompt
    for feature in PLANS["base"]["features"]:
        assert feature in system_prompt


def test_chiave_api_mancante_solleva_500(monkeypatch):
    import services.public_ai_chat_service as svc

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(svc, "check_and_record", _allow)

    with pytest.raises(HTTPException) as exc_info:
        run(svc.chat("ciao", [], "1.2.3.4"))

    assert exc_info.value.status_code == 500


def test_storico_passato_viene_incluso_nei_messaggi(monkeypatch):
    import services.public_ai_chat_service as svc
    from models.public_ai_chat import PublicChatHistoryItem

    created_clients = []
    install_fake_anthropic(make_text_message("risposta"), created_clients)
    monkeypatch.setattr(svc, "check_and_record", _allow)
    monkeypatch.setattr(svc, "public_ai_chat_log_repository", FakeLogRepo())

    history = [
        PublicChatHistoryItem(role="user", text="ciao"),
        PublicChatHistoryItem(role="assistant", text="ciao! come posso aiutarti?"),
    ]
    run(svc.chat("quanto costa il piano pro?", history, "1.2.3.4"))

    messages = created_clients[0].messages.calls[0]["messages"]
    assert len(messages) == 3
    assert messages[0] == {"role": "user", "content": "ciao"}
    assert messages[-1] == {"role": "user", "content": "quanto costa il piano pro?"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
