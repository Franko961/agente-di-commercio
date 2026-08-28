"""
Test per AiService.list_pending_actions(), che espone come endpoint
GET /api/ai/pending-actions: recupera le azioni economiche (add_offer,
add_expense sopra soglia) proposte dall'AI e ancora "in_attesa", nel formato
già atteso dal componente frontend AIActionConfirm (tool_name, resolved_input,
log_id).

Prima di questo metodo/endpoint, le azioni "in_attesa" esistevano solo nella
risposta della singola chiamata a /chat che le aveva create: se l'utente
chiudeva il pannello, ricaricava la pagina o cambiava schermata, la scheda di
conferma spariva senza modo di recuperarla (pur restando il record 'in_attesa'
nel DB, raggiungibile solo da /api/ai/actions?status=in_attesa, che però non
restituisce il formato atteso da AIActionConfirm).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_pending_actions.py -v
"""

import asyncio
import sys

sys.path.insert(0, ".")

from tests.test_ai_tool_forcing import (
    FAKE_USER,
    Payload,
    build_service,
    build_service_with_offer,
    install_fake_anthropic,
    make_message,
    make_text_block,
    make_tool_use_block,
)


def run(coro):
    return asyncio.run(coro)


def test_azione_in_attesa_viene_restituita_nel_formato_atteso_dal_frontend():
    """Un'offerta proposta (in_attesa) deve comparire in list_pending_actions
    con esattamente i campi che AIActionConfirm usa: log_id, tool_name,
    resolved_input."""
    responses = {
        "responses": [
            make_message(
                [
                    make_tool_use_block(
                        "add_offer",
                        {
                            "client_name": "Rossi",
                            "mandante_name": "Paginesi",
                            "total_amount": 1500,
                            "accepted": False,
                        },
                        "tu_1",
                    )
                ],
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
    log_id = result["pending_actions"][0]["log_id"]

    pending = run(service.list_pending_actions(FAKE_USER["id"]))

    assert len(pending) == 1
    assert pending[0]["log_id"] == log_id
    assert pending[0]["tool_name"] == "add_offer"
    assert pending[0]["resolved_input"]["client_name"] == "Rossi Srl"
    assert pending[0]["channel"] == "voice"


def test_azione_confermata_non_compare_piu_tra_le_pendenti():
    responses = {
        "responses": [
            make_message(
                [
                    make_tool_use_block(
                        "add_offer",
                        {
                            "client_name": "Rossi",
                            "mandante_name": "Paginesi",
                            "total_amount": 800,
                        },
                        "tu_1",
                    )
                ],
                stop_reason="tool_use",
            ),
            make_message([make_text_block("Ok.")], stop_reason="end_turn"),
        ]
    }
    install_fake_anthropic(responses)
    service, offer_repo = build_service_with_offer()

    payload = Payload("registra vendita 800 euro Rossi Paginesi")
    result = run(service.chat(FAKE_USER, payload))
    pending = result["pending_actions"][0]
    log_id = pending["log_id"]

    run(
        service.execute_confirmed_action(
            FAKE_USER,
            {
                "tool_name": "add_offer",
                "resolved_input": pending["resolved_input"],
                "log_id": log_id,
            },
        )
    )

    still_pending = run(service.list_pending_actions(FAKE_USER["id"]))
    assert still_pending == []


def test_azione_annullata_non_compare_piu_tra_le_pendenti():
    responses = {
        "responses": [
            make_message(
                [
                    make_tool_use_block(
                        "add_offer",
                        {
                            "client_name": "Rossi",
                            "mandante_name": "Paginesi",
                            "total_amount": 800,
                        },
                        "tu_1",
                    )
                ],
                stop_reason="tool_use",
            ),
            make_message([make_text_block("Ok.")], stop_reason="end_turn"),
        ]
    }
    install_fake_anthropic(responses)
    service, offer_repo = build_service_with_offer()

    payload = Payload("registra vendita 800 euro Rossi Paginesi")
    result = run(service.chat(FAKE_USER, payload))
    log_id = result["pending_actions"][0]["log_id"]

    run(service.cancel_pending_action(FAKE_USER, log_id))

    still_pending = run(service.list_pending_actions(FAKE_USER["id"]))
    assert still_pending == []


def test_azioni_gia_eseguite_subito_non_compaiono_tra_le_pendenti():
    """add_client viene eseguito subito (status 'eseguita'): non deve mai
    comparire come azione pendente."""
    responses = {
        "responses": [
            make_message(
                [
                    make_tool_use_block(
                        "add_client", {"company_name": "Bar Rossi"}, "tu_1"
                    )
                ],
                stop_reason="tool_use",
            ),
            make_message([make_text_block("Fatto.")], stop_reason="end_turn"),
        ]
    }
    install_fake_anthropic(responses)
    service, client_repo = build_service()

    payload = Payload("aggiungi cliente Bar Rossi")
    run(service.chat(FAKE_USER, payload))

    pending = run(service.list_pending_actions(FAKE_USER["id"]))
    assert pending == []


def test_pending_actions_filtra_per_utente():
    service, _ = build_service()
    run(
        service.action_log_repo.insert(
            {
                "id": "l1",
                "user_id": "user-1",
                "tool_name": "add_offer",
                "status": "in_attesa",
                "resolved_params": {"client_name": "Rossi"},
                "channel": "voice",
            }
        )
    )
    run(
        service.action_log_repo.insert(
            {
                "id": "l2",
                "user_id": "user-2",
                "tool_name": "add_offer",
                "status": "in_attesa",
                "resolved_params": {"client_name": "Verdi"},
                "channel": "chat",
            }
        )
    )
    pending = run(service.list_pending_actions("user-1"))
    assert len(pending) == 1
    assert pending[0]["log_id"] == "l1"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
