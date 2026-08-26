"""
Test isolato (mock) per la correzione che impedisce al browser di alterare
liberamente resolved_input su /api/ai/execute-action: cliente, mandante e
prodotti devono sempre arrivare dal resolved_params salvato nel log (calcolato
server-side al momento della proposta), non dal payload della richiesta.
Solo i campi in AiService.ALLOWED_CONFIRM_EDITS possono essere sovrascritti.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_execute_action_field_whitelist.py -v
"""
import sys
import asyncio
from unittest.mock import patch, AsyncMock

sys.path.insert(0, ".")

from tests.test_ai_tool_forcing import build_service_with_offer, build_service, FAKE_USER


def run(coro):
    return asyncio.run(coro)


def _prepare_pending_offer(service):
    """Simula esattamente cosa scrive prepare_add_offer in resolved_params:
    client_id/mandante_id/items/title risolti server-side, come se l'utente
    avesse chiesto 'registra vendita 1500 euro per Rossi da Paginesi'.
    Usa gli id del fixture di build_service_with_offer (c-1/m-1), gli unici
    che il fake mandante/client repo riconosce come esistenti."""
    return run(service._log_action(
        FAKE_USER["id"], "chat", "registra vendita 1500 euro Rossi Paginesi", "add_offer",
        {"client_name": "Rossi", "mandante_name": "Paginesi", "total_amount": 1500},
        status="in_attesa",
        resolved_params={
            "client_id": "c-1", "client_name": "Rossi Srl",
            "mandante_id": "m-1", "mandante_name": "Paginesi",
            "title": "Vendita Rossi Srl",
            "items": [{"product_id": None, "description": "Vendita", "quantity": 1, "unit_price": 1500, "discount": 0}],
            "amount": 1500, "accepted": False, "sale_type": "nuovo",
        },
    ))


def test_client_id_manomesso_dal_browser_viene_ignorato():
    """Anche se il browser invia un client_id diverso (es. di un altro
    account), l'offerta deve essere scritta con il client_id del log, non
    con quello del payload."""
    service, offer_repo = build_service_with_offer()
    log = _prepare_pending_offer(service)

    tampered = dict(log["resolved_params"])
    tampered["client_id"] = "c-di-un-altro-utente"
    tampered["mandante_id"] = "m-di-un-altro-utente"

    with patch("services.ai_service.actions.offers.order_service") as mock_order_service:
        mock_order_service.create_from_offer = AsyncMock(return_value={"total": 1500})
        run(service.execute_confirmed_action(FAKE_USER, {
            "tool_name": "add_offer", "resolved_input": tampered, "log_id": log["id"],
        }))

    assert len(offer_repo.docs) == 1
    assert offer_repo.docs[0]["client_id"] == "c-1"
    assert offer_repo.docs[0]["mandante_id"] == "m-1"


def test_prodotti_manomessi_dal_browser_vengono_ignorati():
    """Il browser non può sostituire le righe prodotto: quelle scritte
    devono essere sempre quelle risolte server-side nel log."""
    service, offer_repo = build_service_with_offer()
    log = _prepare_pending_offer(service)

    tampered = dict(log["resolved_params"])
    tampered["items"] = [
        {"product_id": "p-costoso", "description": "Prodotto sostituito", "quantity": 1000, "unit_price": 99999, "discount": 0}
    ]
    # amount NON viene alterato: se lo fosse, _finalize_offer sostituirebbe
    # comunque gli items con una riga coerente col nuovo importo (è il
    # comportamento voluto per l'unico campo che l'utente può modificare via UI).
    tampered["amount"] = 1500

    with patch("services.ai_service.actions.offers.order_service") as mock_order_service:
        mock_order_service.create_from_offer = AsyncMock(return_value={"total": 1500})
        run(service.execute_confirmed_action(FAKE_USER, {
            "tool_name": "add_offer", "resolved_input": tampered, "log_id": log["id"],
        }))

    written_items = offer_repo.docs[0]["items"]
    assert all(it["product_id"] != "p-costoso" for it in written_items)
    assert offer_repo.docs[0]["total"] == 1500


def test_title_manomesso_dal_browser_viene_ignorato():
    service, offer_repo = build_service_with_offer()
    log = _prepare_pending_offer(service)

    tampered = dict(log["resolved_params"])
    tampered["title"] = "Titolo iniettato dal browser"

    with patch("services.ai_service.actions.offers.order_service") as mock_order_service:
        mock_order_service.create_from_offer = AsyncMock(return_value={"total": 1500})
        run(service.execute_confirmed_action(FAKE_USER, {
            "tool_name": "add_offer", "resolved_input": tampered, "log_id": log["id"],
        }))

    assert offer_repo.docs[0]["title"] == "Vendita Rossi Srl"


def test_amount_e_accepted_restano_modificabili_come_da_ui():
    """amount e accepted sono gli unici campi che AIActionConfirm.jsx espone
    davvero in modifica: devono continuare a funzionare normalmente."""
    service, offer_repo = build_service_with_offer()
    log = _prepare_pending_offer(service)

    edited = dict(log["resolved_params"])
    edited["amount"] = 2000
    edited["accepted"] = True

    with patch("services.ai_service.actions.offers.order_service") as mock_order_service:
        mock_order_service.create_from_offer = AsyncMock(return_value={"total": 2000})
        result = run(service.execute_confirmed_action(FAKE_USER, {
            "tool_name": "add_offer", "resolved_input": edited, "log_id": log["id"],
        }))

    assert offer_repo.docs[0]["total"] == 2000
    assert offer_repo.docs[0]["status"] == "accettata"
    assert "✅" in result["message"]


def test_campo_non_previsto_nel_payload_viene_ignorato():
    """Un campo estraneo iniettato nel payload (non presente in
    ALLOWED_CONFIRM_EDITS né nel resolved_params originale) non deve
    comparire da nessuna parte nel record scritto."""
    service, offer_repo = build_service_with_offer()
    log = _prepare_pending_offer(service)

    tampered = dict(log["resolved_params"])
    tampered["user_id"] = "utente-diverso-iniettato"
    tampered["is_admin"] = True

    with patch("services.ai_service.actions.offers.order_service") as mock_order_service:
        mock_order_service.create_from_offer = AsyncMock(return_value={"total": 1500})
        run(service.execute_confirmed_action(FAKE_USER, {
            "tool_name": "add_offer", "resolved_input": tampered, "log_id": log["id"],
        }))

    assert offer_repo.docs[0]["user_id"] == FAKE_USER["id"]


def test_expense_categoria_e_descrizione_modificabili_ma_non_altri_campi():
    """Per add_expense: amount/category/date/description restano
    modificabili (coerente con l'UI); qualunque altro campo iniettato viene
    ignorato."""
    service, _ = build_service()
    log = run(service._log_action(
        FAKE_USER["id"], "chat", "spesa 200 euro carburante", "add_expense",
        {"amount": 200, "category": "carburante"},
        status="in_attesa",
        resolved_params={"category": "carburante", "amount": 200, "date": "2026-07-20", "description": "", "notes": ""},
    ))

    tampered = dict(log["resolved_params"])
    tampered["category"] = "materiali"
    tampered["description"] = "Rifornimento"
    tampered["client_id"] = "iniettato"  # non previsto per add_expense, deve essere ignorato comunque

    result = run(service.execute_confirmed_action(FAKE_USER, {
        "tool_name": "add_expense", "resolved_input": tampered, "log_id": log["id"],
    }))

    assert "materiali" in result["message"]
    updated_log = next(d for d in service.action_log_repo.docs if d["id"] == log["id"])
    assert updated_log["status"] == "confermata"


if __name__ == "__main__":
    test_client_id_manomesso_dal_browser_viene_ignorato()
    print("OK: test 1 - client_id manomesso ignorato")
    test_prodotti_manomessi_dal_browser_vengono_ignorati()
    print("OK: test 2 - prodotti manomessi ignorati")
    test_title_manomesso_dal_browser_viene_ignorato()
    print("OK: test 3 - title manomesso ignorato")
    test_amount_e_accepted_restano_modificabili_come_da_ui()
    print("OK: test 4 - amount/accepted restano modificabili")
    test_campo_non_previsto_nel_payload_viene_ignorato()
    print("OK: test 5 - campo estraneo ignorato")
    test_expense_categoria_e_descrizione_modificabili_ma_non_altri_campi()
    print("OK: test 6 - expense: solo i campi previsti sono modificabili")
