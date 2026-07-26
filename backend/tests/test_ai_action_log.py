"""
Test isolato (mock) per il registro azioni AI (audit log): verifica che ogni
azione dell'assistente — sia quelle eseguite subito (add_client, ecc.) sia
quelle economiche che passano dalla scheda di conferma (add_offer,
add_expense) — lasci una traccia coerente in AiActionLogRepository, con lo
stato giusto in ogni fase (proposta / confermata / annullata / fallita).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_action_log.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

from tests.test_ai_tool_forcing import (
    build_service,
    build_service_with_offer,
    install_fake_anthropic,
    make_message,
    make_text_block,
    make_tool_use_block,
    Payload,
    FAKE_USER,
)


def run(coro):
    return asyncio.run(coro)


def test_tool_diretto_eseguito_subito_viene_loggato_come_eseguita():
    """add_client scrive subito: la voce di log deve comparire già con stato
    'eseguita', senza passare da 'in_attesa'."""
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
    payload.channel = "chat"
    run(service.chat(FAKE_USER, payload))

    logs = service.action_log_repo.docs
    assert len(logs) == 1
    assert logs[0]["tool_name"] == "add_client"
    assert logs[0]["status"] == "eseguita"
    assert logs[0]["channel"] == "chat"
    assert logs[0]["raw_input"] == "aggiungi cliente Bar Rossi"
    assert logs[0]["user_id"] == "user-1"


def test_offerta_proposta_resta_in_attesa_finche_non_confermata():
    """add_offer (canale voce) deve generare una voce 'in_attesa' con un
    log_id restituito nelle pending_actions, così il frontend può richiamarlo
    su conferma/annullamento. Usa accepted=False (bozza): con accepted=True
    la conferma invocherebbe anche order_service, che nei test non è iniettato
    come fake e userebbe il DB reale (stesso motivo per cui l'analogo test in
    test_ai_tool_forcing.py non arriva mai a testare la conferma con
    accepted=True)."""
    responses = {
        "responses": [
            make_message(
                [make_tool_use_block(
                    "add_offer",
                    {"client_name": "Rossi", "mandante_name": "Paginesi",
                     "total_amount": 1500, "accepted": False},
                    "tu_1",
                )],
                stop_reason="tool_use",
            ),
            make_message(
                [make_text_block("Ho preparato la vendita, conferma per registrarla.")],
                stop_reason="end_turn",
            ),
        ]
    }
    install_fake_anthropic(responses)
    service, offer_repo = build_service_with_offer()

    payload = Payload("registra una vendita di 1500 euro per Rossi da Paginesi")
    payload.channel = "voice"
    result = run(service.chat(FAKE_USER, payload))

    logs = service.action_log_repo.docs
    assert len(logs) == 1
    assert logs[0]["status"] == "in_attesa"
    assert logs[0]["channel"] == "voice"
    assert logs[0]["tool_name"] == "add_offer"
    assert len(offer_repo.docs) == 0  # non ancora scritta

    pending = result["pending_actions"]
    assert len(pending) == 1
    log_id = pending[0]["log_id"]
    assert log_id == logs[0]["id"]

    # L'utente conferma dalla scheda -> execute_confirmed_action
    confirm_payload = {
        "tool_name": "add_offer",
        "resolved_input": pending[0]["resolved_input"],
        "log_id": log_id,
    }
    run(service.execute_confirmed_action(FAKE_USER, confirm_payload))

    assert len(offer_repo.docs) == 1  # ora sì, scritta
    updated_log = next(d for d in service.action_log_repo.docs if d["id"] == log_id)
    assert updated_log["status"] == "confermata"
    assert updated_log["confirmed_at"] is not None
    assert "✅" in updated_log["result"]


def test_offerta_proposta_e_poi_annullata():
    """Se l'utente preme 'Annulla' sulla scheda di conferma, la voce di log
    deve passare a 'annullata' e nessun record deve essere scritto."""
    responses = {
        "responses": [
            make_message(
                [make_tool_use_block(
                    "add_offer",
                    {"client_name": "Rossi", "mandante_name": "Paginesi", "total_amount": 800},
                    "tu_1",
                )],
                stop_reason="tool_use",
            ),
            make_message(
                [make_text_block("Ho preparato la vendita, conferma per registrarla.")],
                stop_reason="end_turn",
            ),
        ]
    }
    install_fake_anthropic(responses)
    service, offer_repo = build_service_with_offer()

    payload = Payload("registra vendita 800 euro Rossi Paginesi")
    result = run(service.chat(FAKE_USER, payload))
    log_id = result["pending_actions"][0]["log_id"]

    run(service.cancel_pending_action(FAKE_USER, log_id))

    assert len(offer_repo.docs) == 0
    updated_log = next(d for d in service.action_log_repo.docs if d["id"] == log_id)
    assert updated_log["status"] == "annullata"


def test_list_actions_filtra_per_utente_e_rispetta_i_filtri_del_fake_repo():
    service, _ = build_service()
    run(service.action_log_repo.insert({
        "id": "l1", "user_id": "user-1", "tool_name": "add_client", "status": "eseguita",
    }))
    run(service.action_log_repo.insert({
        "id": "l2", "user_id": "user-2", "tool_name": "add_client", "status": "eseguita",
    }))
    results = run(service.list_actions("user-1"))
    assert len(results) == 1
    assert results[0]["id"] == "l1"
