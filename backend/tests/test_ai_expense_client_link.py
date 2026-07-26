"""
Verifica che il tool add_expense possa collegare la spesa a un cliente
esistente (es. "registra 40 euro di pranzo con Rossi"), risolvendo il nome
server-side in prepare_add_expense — come già avviene per client_name in
prepare_add_offer — invece di lasciare sempre client_id=None.

Il collegamento è opzionale (a differenza delle offerte): un cliente non
trovato non deve impedire la registrazione della spesa, solo lasciarla senza
collegamento con un avviso nel messaggio finale.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_expense_client_link.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

from tests.test_ai_tool_forcing import (
    build_service, FakeClientRepo, FakeSimpleRepo, FakeAiRepo, FakeActionLogRepo,
)


def run(coro):
    return asyncio.run(coro)


class FakeExpenseRepo(FakeSimpleRepo):
    """Traccia gli inserimenti, per verificare cosa viene effettivamente
    scritto sul CRM (in particolare client_id)."""

    def __init__(self):
        self.docs = []

    async def insert(self, doc):
        self.docs.append(doc)
        return doc


def build_service_with_expense_tracking():
    """Variante di build_service() con un expense_repo che traccia gli
    inserimenti (build_service usa FakeSimpleRepo, che scarta i documenti)."""
    from services.ai_service import AiService
    client_repo = FakeClientRepo()
    expense_repo = FakeExpenseRepo()
    service = AiService(
        repo=FakeAiRepo(),
        client_repo=client_repo,
        appointment_repo=FakeSimpleRepo(),
        lead_repo=FakeSimpleRepo(),
        offer_repo=FakeSimpleRepo(),
        commission_repo=FakeSimpleRepo(),
        mandante_repo=FakeSimpleRepo(),
        product_repo=FakeSimpleRepo(),
        expense_repo=expense_repo,
        action_log_repo=FakeActionLogRepo(),
    )
    return service, client_repo, expense_repo


def test_prepare_expense_risolve_il_cliente_quando_indicato():
    service, client_repo = build_service()
    client_repo.docs.append({"id": "c-1", "user_id": "user-1", "company_name": "Bar Rossi"})

    result = run(service.prepare_add_expense(
        {"category": "vitto", "amount": 40, "client_name": "Rossi"}, "user-1",
    ))

    assert "error" not in result
    assert result["resolved_input"]["client_id"] == "c-1"
    assert result["resolved_input"]["client_name"] == "Bar Rossi"
    assert result["resolved_input"]["client_not_found"] is None


def test_prepare_expense_senza_client_name_non_cerca_alcun_cliente():
    service, client_repo = build_service()
    client_repo.docs.append({"id": "c-1", "user_id": "user-1", "company_name": "Bar Rossi"})

    result = run(service.prepare_add_expense({"category": "vitto", "amount": 40}, "user-1"))

    assert result["resolved_input"]["client_id"] is None
    assert result["resolved_input"]["client_name"] is None


def test_prepare_expense_con_cliente_non_trovato_non_blocca_la_spesa():
    """A differenza delle offerte, un cliente non trovato è solo un avviso:
    la spesa resta 'solo tracciamento' e viene comunque preparata."""
    service, client_repo = build_service()

    result = run(service.prepare_add_expense(
        {"category": "vitto", "amount": 40, "client_name": "Cliente Inesistente"}, "user-1",
    ))

    assert "error" not in result
    assert result["resolved_input"]["client_id"] is None
    assert result["resolved_input"]["client_not_found"] == "Cliente Inesistente"


def test_finalize_expense_scrive_il_client_id_risolto():
    service, _, expense_repo = build_service_with_expense_tracking()
    msg = run(service._finalize_expense("user-1", {
        "category": "vitto", "amount": 40, "date": "2026-07-21",
        "client_id": "c-1", "client_name": "Bar Rossi",
    }))

    assert msg.startswith("✅")
    assert "Bar Rossi" in msg
    doc = expense_repo.docs[0]
    assert doc["client_id"] == "c-1"


def test_finalize_expense_senza_client_id_resta_none():
    service, _, expense_repo = build_service_with_expense_tracking()
    msg = run(service._finalize_expense("user-1", {
        "category": "vitto", "amount": 40, "date": "2026-07-21",
    }))

    assert msg.startswith("✅")
    doc = expense_repo.docs[0]
    assert doc["client_id"] is None


def test_finalize_expense_avvisa_se_cliente_non_trovato():
    service, _, expense_repo = build_service_with_expense_tracking()
    msg = run(service._finalize_expense("user-1", {
        "category": "vitto", "amount": 40, "date": "2026-07-21",
        "client_not_found": "Cliente Inesistente",
    }))

    assert msg.startswith("✅")  # la spesa viene comunque registrata
    assert "non trovato" in msg
    doc = expense_repo.docs[0]
    assert doc["client_id"] is None


def test_client_id_non_e_modificabile_dal_browser_su_execute_action():
    """client_id/client_name non sono tra gli ALLOWED_CONFIRM_EDITS per
    add_expense: anche se il payload di /execute-action tentasse di
    impostare un client_id diverso, execute_confirmed_action deve ignorarlo
    e usare solo quello già risolto server-side in resolved_params."""
    service, client_repo, expense_repo = build_service_with_expense_tracking()
    client_repo.docs.append({"id": "c-1", "user_id": "user-1", "company_name": "Bar Rossi"})

    run(service.action_log_repo.insert({
        "id": "log-1", "user_id": "user-1", "tool_name": "add_expense", "status": "in_attesa",
        "resolved_params": {
            "category": "vitto", "amount": 40, "date": "2026-07-21",
            "client_id": "c-1", "client_name": "Bar Rossi",
        },
    }))

    run(service.execute_confirmed_action({"id": "user-1"}, {
        "tool_name": "add_expense",
        "resolved_input": {"client_id": "c-999-manomesso", "amount": 40},  # tentativo di manomissione
        "log_id": "log-1",
    }))

    doc = expense_repo.docs[0]
    assert doc["client_id"] == "c-1"  # non "c-999-manomesso"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
