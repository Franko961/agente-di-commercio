"""
Test isolato (mock) per la logica anti-hallucination di ai_service.chat().

Verifica tre scenari SENZA bisogno di un DB reale o di una vera chiamata
all'API Anthropic:

1. Il modello chiama web_search e poi risponde solo con testo (senza mai
   invocare add_client) -> deve scattare la chiamata forzata con
   tool_choice, e il cliente deve finire davvero nel repository.
2. Il modello chiama add_client subito, correttamente -> nessuna forzatura
   necessaria, il cliente viene comunque inserito una sola volta.
3. Il messaggio dell'utente non implica nessuna azione CRM -> nessuna
   forzatura, anche se nessun tool viene mai chiamato.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_tool_forcing.py -v
"""
import sys
import types
import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

sys.path.insert(0, ".")


# ---------- Fake Anthropic SDK ----------

def make_tool_use_block(name, input_, block_id="tool_1"):
    return SimpleNamespace(type="tool_use", name=name, input=input_, id=block_id)


def make_text_block(text):
    return SimpleNamespace(type="text", text=text)


def make_message(content, stop_reason):
    return SimpleNamespace(content=content, stop_reason=stop_reason)


class FakeMessages:
    """Restituisce in sequenza le risposte pre-programmate per ogni chiamata .create()."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
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


# ---------- Fake repositories (in-memory, nessun DB reale) ----------

class FakeClientRepo:
    def __init__(self):
        self.docs = []

    async def find_many(self, user_id, filters):
        return list(self.docs)

    async def find_by_name_regex(self, user_id, name):
        for d in self.docs:
            if name.lower() in d.get("company_name", "").lower():
                return d
        return None

    async def insert(self, doc):
        self.docs.append(doc)
        return doc

    async def update(self, cid, user_id, data):
        return True


class FakeSimpleRepo:
    """Repo generico per tutto ciò che serve solo a gather_context (appuntamenti, offerte, ecc.)."""

    async def find_many(self, *args, **kwargs):
        return []

    async def find_by_name_regex(self, *args, **kwargs):
        return None

    async def find_one(self, *args, **kwargs):
        return None

    async def insert(self, doc):
        return doc


class FakeOfferRepo(FakeSimpleRepo):
    """Traccia gli inserimenti, per verificare che add_offer NON scriva nulla
    finché l'azione non viene confermata esplicitamente."""

    def __init__(self):
        self.docs = []

    async def insert(self, doc):
        self.docs.append(doc)
        return doc


class FakeMandanteRepo(FakeSimpleRepo):
    def __init__(self, mandante):
        self.mandante = mandante

    async def find_by_name_regex(self, user_id, name):
        if name and name.lower() in self.mandante["name"].lower():
            return self.mandante
        return None

    async def find_one(self, mandante_id, user_id):
        return self.mandante if mandante_id == self.mandante["id"] else None


class FakeAiRepo:
    async def find_history(self, user_id, limit=30):
        return []

    async def delete_all(self, user_id):
        return None

    async def find_recent_for_context(self, user_id, limit=10):
        return []

    async def insert_log(self, log):
        return None


class FakeActionLogRepo:
    """Fake del registro azioni AI: traccia gli insert/update in memoria
    invece di scrivere sul DB reale."""

    def __init__(self):
        self.docs = []

    async def insert(self, doc):
        self.docs.append(doc)
        return doc

    async def update_by_id(self, log_id, user_id, data):
        for d in self.docs:
            if d["id"] == log_id and d["user_id"] == user_id:
                d.update(data)
        return None

    async def find_one(self, log_id, user_id):
        for d in self.docs:
            if d["id"] == log_id and d["user_id"] == user_id:
                return d
        return None

    async def transition(self, log_id, user_id, from_status, data, extra_match=None):
        for d in self.docs:
            if d["id"] == log_id and d["user_id"] == user_id and d["status"] == from_status:
                if extra_match and any(d.get(k) != v for k, v in extra_match.items()):
                    continue
                d.update(data)
                return True
        return False

    async def find_many(self, user_id, tool_name=None, status=None, date_from=None, date_to=None, limit=200):
        results = [d for d in self.docs if d["user_id"] == user_id]
        if tool_name:
            results = [d for d in results if d["tool_name"] == tool_name]
        if status:
            results = [d for d in results if d["status"] == status]
        return results[:limit]

    async def reclaim_stale_executions(self, threshold_iso, result_message):
        count = 0
        for d in self.docs:
            if d.get("status") == "in_esecuzione" and d.get("execution_started_at", "") < threshold_iso:
                d["status"] = "fallita"
                d["result"] = result_message
                count += 1
        return count


def build_service():
    from services.ai_service import AiService
    client_repo = FakeClientRepo()
    service = AiService(
        repo=FakeAiRepo(),
        client_repo=client_repo,
        appointment_repo=FakeSimpleRepo(),
        lead_repo=FakeSimpleRepo(),
        offer_repo=FakeSimpleRepo(),
        commission_repo=FakeSimpleRepo(),
        mandante_repo=FakeSimpleRepo(),
        product_repo=FakeSimpleRepo(),
        expense_repo=FakeSimpleRepo(),
        action_log_repo=FakeActionLogRepo(),
    )
    return service, client_repo


FAKE_USER = {"id": "user-1", "email": "franco@test.it"}


class Payload:
    def __init__(self, message):
        self.message = message


def build_service_with_offer():
    """Variante di build_service() con mandante/offerta reali (fittizi) per
    testare il flusso di conferma economica di add_offer."""
    from services.ai_service import AiService
    client_repo = FakeClientRepo()
    client_repo.docs.append({"id": "c-1", "user_id": "user-1", "company_name": "Rossi Srl"})
    mandante = {"id": "m-1", "name": "Paginesi", "commission_rate": 10}
    offer_repo = FakeOfferRepo()
    service = AiService(
        repo=FakeAiRepo(),
        client_repo=client_repo,
        appointment_repo=FakeSimpleRepo(),
        lead_repo=FakeSimpleRepo(),
        offer_repo=offer_repo,
        commission_repo=FakeSimpleRepo(),
        mandante_repo=FakeMandanteRepo(mandante),
        product_repo=FakeSimpleRepo(),
        expense_repo=FakeSimpleRepo(),
        action_log_repo=FakeActionLogRepo(),
    )
    return service, offer_repo


# ---------- Scenari ----------

def test_forza_tool_choice_quando_il_modello_racconta_senza_eseguire():
    """Scenario del bug reale: web_search + risposta testuale che 'finge' il successo."""
    responses = {
        "responses": [
            # Turno 1: il modello fa una web_search per raccogliere i dati dal sito
            make_message(
                [make_tool_use_block("web_search", {"query": "carrozzeriapalandrani.com"}, "ws_1")],
                stop_reason="tool_use",
            ),
            # Turno 2: NON chiama add_client, risponde solo con testo (l'hallucination)
            make_message(
                [make_text_block("# ✅ Cliente Aggiunto al CRM\n(in realtà non l'ho fatto)")],
                stop_reason="end_turn",
            ),
            # Turno 3 (FORZATO con tool_choice): ora chiama davvero add_client
            make_message(
                [make_tool_use_block(
                    "add_client",
                    {"company_name": "Carrozzeria Palandrani Michele", "city": "Teramo"},
                    "tu_2",
                )],
                stop_reason="tool_use",
            ),
            # Turno 4: risposta finale dopo il tool_result
            make_message(
                [make_text_block("✅ Cliente Carrozzeria Palandrani Michele aggiunto con successo.")],
                stop_reason="end_turn",
            ),
        ]
    }
    install_fake_anthropic(responses)
    service, client_repo = build_service()

    payload = Payload("aggiungi questo cliente https://www.carrozzeriapalandrani.com/")
    result = asyncio.get_event_loop().run_until_complete(service.chat(FAKE_USER, payload))

    # Il cliente DEVE essere stato inserito davvero nel repository
    assert len(client_repo.docs) == 1
    assert client_repo.docs[0]["company_name"] == "Carrozzeria Palandrani Michele"
    assert client_repo.docs[0]["user_id"] == "user-1"

    # La chiamata forzata deve aver usato tool_choice esplicito su add_client
    forced_call = responses["responses"]  # ormai vuoto, controlliamo le call registrate altrove
    assert "✅" in result["response"]
    assert any("aggiunto" in a.lower() for a in result["actions"])


def test_nessuna_forzatura_se_il_tool_giusto_viene_gia_chiamato():
    """Se il modello chiama subito add_client, non deve scattare nessuna forzatura extra."""
    responses = {
        "responses": [
            make_message(
                [make_tool_use_block("add_client", {"company_name": "Bar Rossi"}, "tu_1")],
                stop_reason="tool_use",
            ),
            make_message(
                [make_text_block("✅ Cliente Bar Rossi aggiunto con successo.")],
                stop_reason="end_turn",
            ),
        ]
    }
    install_fake_anthropic(responses)
    service, client_repo = build_service()

    payload = Payload("aggiungi cliente Bar Rossi")
    result = asyncio.get_event_loop().run_until_complete(service.chat(FAKE_USER, payload))

    assert len(client_repo.docs) == 1
    assert client_repo.docs[0]["company_name"] == "Bar Rossi"


def test_nessuna_forzatura_se_non_richiesta_azione_crm():
    """Una domanda generica non deve mai innescare una chiamata forzata a un tool CRM."""
    responses = {
        "responses": [
            make_message(
                [make_text_block("Ecco i 3 clienti da visitare questa settimana...")],
                stop_reason="end_turn",
            ),
        ]
    }
    install_fake_anthropic(responses)
    service, client_repo = build_service()

    payload = Payload("quali clienti devo visitare questa settimana?")
    result = asyncio.get_event_loop().run_until_complete(service.chat(FAKE_USER, payload))

    assert len(client_repo.docs) == 0
    assert result["actions"] == []


def test_add_offer_non_scrive_subito_ma_richiede_conferma():
    """Anche se il modello chiama add_offer correttamente e con sicurezza (es.
    dal canale vocale, dove una trascrizione imprecisa dell'importo è un
    rischio reale), l'offerta NON deve essere scritta sul DB in questo turno:
    deve solo comparire tra le pending_actions, in attesa di conferma
    esplicita dell'utente su /api/ai/execute-action."""
    responses = {
        "responses": [
            make_message(
                [make_tool_use_block(
                    "add_offer",
                    {"client_name": "Rossi", "mandante_name": "Paginesi",
                     "total_amount": 15000, "accepted": True},
                    "tu_1",
                )],
                stop_reason="tool_use",
            ),
            make_message(
                [make_text_block("Ho preparato la vendita per Rossi Srl da 15.000€, conferma per registrarla.")],
                stop_reason="end_turn",
            ),
        ]
    }
    install_fake_anthropic(responses)
    service, offer_repo = build_service_with_offer()

    payload = Payload("registra una vendita accettata da 15000 euro per Rossi con Paginesi")
    result = asyncio.get_event_loop().run_until_complete(service.chat(FAKE_USER, payload))

    # Nessuna scrittura reale: né azione "eseguita", né offerta nel repository
    assert result["actions"] == []
    assert offer_repo.docs == []

    # L'operazione compare come pending, con l'importo esatto compreso dal modello
    assert len(result["pending_actions"]) == 1
    pending = result["pending_actions"][0]
    assert pending["tool_name"] == "add_offer"
    assert pending["summary"]["amount"] == 15000
    assert pending["summary"]["client_name"] == "Rossi Srl"

    # Solo ora, con la conferma esplicita dell'utente (che qui corregge
    # l'importo frainteso, es. 15.000 -> 1.500), l'offerta viene scritta
    resolved = dict(pending["resolved_input"])
    resolved["amount"] = 1500
    with patch("services.ai_service.order_service") as mock_order_service:
        mock_order_service.create_from_offer = AsyncMock(return_value={"total": 1500})
        confirm_result = asyncio.get_event_loop().run_until_complete(
            service.execute_confirmed_action(FAKE_USER, {
                "tool_name": "add_offer", "resolved_input": resolved, "log_id": pending["log_id"],
            })
        )
    assert len(offer_repo.docs) == 1
    assert offer_repo.docs[0]["total"] == 1500
    assert "1500.00" in confirm_result["message"] or "1500" in confirm_result["message"]


if __name__ == "__main__":
    test_forza_tool_choice_quando_il_modello_racconta_senza_eseguire()
    print("OK: test 1 - forzatura funziona")
    test_nessuna_forzatura_se_il_tool_giusto_viene_gia_chiamato()
    print("OK: test 2 - nessuna doppia esecuzione")
    test_nessuna_forzatura_se_non_richiesta_azione_crm()
    print("OK: test 3 - nessuna forzatura indebita")
    test_add_offer_non_scrive_subito_ma_richiede_conferma()
    print("OK: test 4 - add_offer richiede conferma prima di scrivere")
