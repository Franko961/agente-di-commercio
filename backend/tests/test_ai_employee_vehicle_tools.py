"""
Verifica i tool AI add_employee/add_vehicle (services/ai_service.py):
collegano l'assistente conversazionale ai moduli Personale e Flotta, riusando
employee_service.create_employee / vehicle_service.create_vehicle invece di
duplicarne la logica (in particolare la generazione del link personale,
sensibile dal punto di vista della sicurezza).

Copre anche il fix del gate moduli extra: prima di questa modifica il
controllo in chat() guardava solo user["disabled_modules"] (i moduli CORE,
opt-out), che non intercetta affatto i moduli EXTRA (opt-in, es.
"personale"/"flotta") — un account che non li ha mai attivati non li trova
mai in disabled_modules, quindi il vecchio controllo li avrebbe lasciati
passare. Ora usa core.security.module_enabled, corretto per entrambi i tipi.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_ai_employee_vehicle_tools.py -v
"""
import sys
import types
import asyncio
from types import SimpleNamespace

import pytest

sys.path.insert(0, ".")

import services.ai_service as ai_service_mod
from services.ai_service import AiService
from core.exceptions import ValidationAppError


def run(coro):
    return asyncio.run(coro)


async def _allow_ai_chat_rate_limit(*a, **k):
    return True


# ---------- Fake Anthropic SDK (stesso pattern di test_ai_tool_forcing.py) ----------

def make_tool_use_block(name, input_, block_id="tool_1"):
    return SimpleNamespace(type="tool_use", name=name, input=input_, id=block_id)


def make_text_block(text):
    return SimpleNamespace(type="text", text=text)


def make_message(content, stop_reason):
    return SimpleNamespace(content=content, stop_reason=stop_reason)


class FakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)

    def create(self, **kwargs):
        if not self._responses:
            raise AssertionError("Nessuna risposta finta rimasta: troppe chiamate API")
        return self._responses.pop(0)


class FakeAnthropicClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def install_fake_anthropic(responses_holder):
    fake_module = types.ModuleType("anthropic")

    def _Anthropic(api_key=None):
        return FakeAnthropicClient(responses_holder["responses"])

    fake_module.Anthropic = _Anthropic
    sys.modules["anthropic"] = fake_module
    return fake_module


class FakeSimpleRepo:
    async def find_many(self, *args, **kwargs):
        return []

    async def find_by_name_regex(self, *args, **kwargs):
        return None

    async def find_one(self, *args, **kwargs):
        return None

    async def insert(self, doc):
        return doc


class FakeAiRepo:
    async def find_history(self, user_id, limit=30):
        return []

    async def find_recent_for_context(self, user_id, limit=10):
        return []

    async def insert_log(self, log):
        return None

    async def count_since(self, user_id, since_iso):
        return 0


class FakeActionLogRepo:
    def __init__(self):
        self.docs = []

    async def insert(self, doc):
        self.docs.append(doc)
        return doc


def build_chat_service():
    ai_service_mod.check_and_record = _allow_ai_chat_rate_limit
    action_log_repo = FakeActionLogRepo()
    service = AiService(
        repo=FakeAiRepo(), client_repo=FakeSimpleRepo(), appointment_repo=FakeSimpleRepo(),
        lead_repo=FakeSimpleRepo(), offer_repo=FakeSimpleRepo(), commission_repo=FakeSimpleRepo(),
        manual_commission_repo=FakeSimpleRepo(), mandante_repo=FakeSimpleRepo(),
        product_repo=FakeSimpleRepo(), expense_repo=FakeSimpleRepo(), action_log_repo=action_log_repo,
    )
    return service, action_log_repo


class Payload:
    def __init__(self, message):
        self.message = message


# ---------- Fake employee_service / vehicle_service ----------

class FakeEmployeeService:
    def __init__(self):
        self.calls = []

    async def create_employee(self, user, payload):
        self.calls.append((user, payload))
        return {"id": "emp-1", "user_id": user["id"], "name": payload.name,
                "surname": payload.surname, "role": payload.role, "request_token": "faketoken"}


class FakeVehicleService:
    def __init__(self, raise_error=None):
        self.calls = []
        self.raise_error = raise_error

    async def create_vehicle(self, user, payload):
        self.calls.append((user, payload))
        if self.raise_error:
            raise self.raise_error
        return {"id": "veh-1", "user_id": user["id"], "plate": payload.plate,
                "model": payload.model, "type": payload.type}


USER = {"id": "user-1", "email": "franco@test.it"}


# ---------- execute_crm_tool: add_employee ----------

def test_add_employee_tool_usa_employee_service(monkeypatch):
    fake = FakeEmployeeService()
    monkeypatch.setattr(ai_service_mod, "employee_service", fake)
    service = AiService()

    result = run(service.execute_crm_tool(
        "add_employee", {"name": "Mario", "surname": "Rossi", "role": "Autista"}, USER["id"],
    ))

    assert len(fake.calls) == 1
    called_user, payload = fake.calls[0]
    assert called_user["id"] == USER["id"]
    assert payload.name == "Mario"
    assert payload.surname == "Rossi"
    assert payload.role == "Autista"
    assert "Mario Rossi" in result
    assert result.startswith("✅")


def test_add_employee_tool_funziona_senza_cognome(monkeypatch):
    fake = FakeEmployeeService()
    monkeypatch.setattr(ai_service_mod, "employee_service", fake)
    service = AiService()

    result = run(service.execute_crm_tool("add_employee", {"name": "Anna"}, USER["id"]))

    assert result.startswith("✅")
    assert "Anna" in result


# ---------- execute_crm_tool: add_vehicle ----------

def test_add_vehicle_tool_usa_vehicle_service(monkeypatch):
    fake = FakeVehicleService()
    monkeypatch.setattr(ai_service_mod, "vehicle_service", fake)
    service = AiService()

    result = run(service.execute_crm_tool(
        "add_vehicle", {"plate": "AB123CD", "model": "Fiat Ducato", "type": "furgone"}, USER["id"],
    ))

    assert len(fake.calls) == 1
    called_user, payload = fake.calls[0]
    assert called_user["id"] == USER["id"]
    assert payload.plate == "AB123CD"
    assert payload.model == "Fiat Ducato"
    assert "AB123CD" in result
    assert result.startswith("✅")


def test_add_vehicle_tool_default_furgone(monkeypatch):
    fake = FakeVehicleService()
    monkeypatch.setattr(ai_service_mod, "vehicle_service", fake)
    service = AiService()

    run(service.execute_crm_tool("add_vehicle", {"plate": "XY999ZZ"}, USER["id"]))

    _, payload = fake.calls[0]
    assert payload.type == "furgone"


def test_add_vehicle_tool_propaga_errore_targa_duplicata(monkeypatch):
    fake = FakeVehicleService(raise_error=ValidationAppError("Esiste già un mezzo con targa AB123CD"))
    monkeypatch.setattr(ai_service_mod, "vehicle_service", fake)
    service = AiService()

    result = run(service.execute_crm_tool("add_vehicle", {"plate": "AB123CD"}, USER["id"]))

    assert result.startswith("❌")
    assert "AB123CD" in result


# ---------- Gate moduli extra (personale/flotta) dentro chat() ----------

def test_add_employee_bloccato_se_modulo_personale_non_abilitato(monkeypatch):
    """USER non ha "personale" in enabled_extra_modules: il vecchio controllo
    (solo su disabled_modules) lo avrebbe lasciato passare comunque, dato che
    un modulo extra mai attivato non compare in quella lista."""
    fake = FakeEmployeeService()
    monkeypatch.setattr(ai_service_mod, "employee_service", fake)
    responses = {"responses": [
        make_message([make_tool_use_block("add_employee", {"name": "Mario"}, "t1")], stop_reason="tool_use"),
        make_message([make_text_block("Fatto.")], stop_reason="end_turn"),
    ]}
    install_fake_anthropic(responses)
    service, action_log_repo = build_chat_service()

    run(service.chat(USER, Payload("aggiungi il dipendente Mario")))

    assert fake.calls == []  # nessuna scrittura reale
    assert action_log_repo.docs[0]["status"] == "fallita"
    assert "🔒" in action_log_repo.docs[0]["result"]


def test_add_employee_consentito_se_modulo_personale_abilitato(monkeypatch):
    fake = FakeEmployeeService()
    monkeypatch.setattr(ai_service_mod, "employee_service", fake)
    responses = {"responses": [
        make_message([make_tool_use_block("add_employee", {"name": "Mario"}, "t1")], stop_reason="tool_use"),
        make_message([make_text_block("Fatto.")], stop_reason="end_turn"),
    ]}
    install_fake_anthropic(responses)
    service, _ = build_chat_service()
    user = {"id": "user-1", "email": "franco@test.it", "enabled_extra_modules": ["personale"]}

    result = run(service.chat(user, Payload("aggiungi il dipendente Mario")))

    assert len(fake.calls) == 1
    assert any("✅" in a for a in result["actions"])


def test_add_vehicle_bloccato_se_modulo_flotta_non_abilitato(monkeypatch):
    fake = FakeVehicleService()
    monkeypatch.setattr(ai_service_mod, "vehicle_service", fake)
    responses = {"responses": [
        make_message([make_tool_use_block("add_vehicle", {"plate": "AB123CD"}, "t1")], stop_reason="tool_use"),
        make_message([make_text_block("Fatto.")], stop_reason="end_turn"),
    ]}
    install_fake_anthropic(responses)
    service, action_log_repo = build_chat_service()

    run(service.chat(USER, Payload("aggiungi il furgone AB123CD")))

    assert fake.calls == []
    assert action_log_repo.docs[0]["status"] == "fallita"
    assert "🔒" in action_log_repo.docs[0]["result"]
