"""
Test isolato (mock) per la correzione di /api/ai/execute-action: verifica che
un'azione economica confermata (add_offer/add_expense) non possa mai essere
eseguita due volte, e che il servizio rifiuti richieste con log_id assente,
inesistente, non appartenente all'utente, non più "in_attesa", o con un
tool_name diverso da quello registrato nel log.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_execute_action_idempotency.py -v
"""

import asyncio
import sys
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, ".")

from tests.test_ai_tool_forcing import (
    FAKE_USER,
    build_service,
    build_service_with_offer,
)


def run(coro):
    return asyncio.run(coro)


def _prepare_pending_offer(service, offer_repo, amount=1500):
    """Crea direttamente una voce 'in_attesa' nel registro (senza passare dal
    modello AI), così i test si concentrano solo su execute_confirmed_action."""
    log = run(
        service._log_action(
            FAKE_USER["id"],
            "chat",
            "registra vendita",
            "add_offer",
            {
                "client_name": "Rossi",
                "mandante_name": "Paginesi",
                "total_amount": amount,
            },
            status="in_attesa",
            resolved_params={
                "client_id": "c-1",
                "client_name": "Rossi Srl",
                "mandante_id": "m-1",
                "mandante_name": "Paginesi",
                "amount": amount,
            },
        )
    )
    return log


def test_doppia_conferma_concorrente_scrive_una_sola_volta():
    """Due chiamate a execute_confirmed_action con lo stesso log_id (doppio
    clic, retry di rete): solo la prima deve scrivere l'offerta, la seconda
    deve fallire con 409 senza toccare il CRM una seconda volta."""
    service, offer_repo = build_service_with_offer()
    log = _prepare_pending_offer(service, offer_repo)
    confirm_payload = {
        "tool_name": "add_offer",
        "resolved_input": log["resolved_params"],
        "log_id": log["id"],
    }

    with patch(
        "services.ai_service.actions.offers.order_service"
    ) as mock_order_service:
        mock_order_service.create_from_offer = AsyncMock(return_value={"total": 1500})
        first = run(service.execute_confirmed_action(FAKE_USER, dict(confirm_payload)))

        with pytest.raises(HTTPException) as exc_info:
            run(service.execute_confirmed_action(FAKE_USER, dict(confirm_payload)))

    assert "✅" in first["message"]
    assert len(offer_repo.docs) == 1  # scritta una sola volta, non due
    assert exc_info.value.status_code == 409


def test_log_id_mancante_viene_rifiutato():
    """Senza log_id la richiesta va rifiutata subito: prima del fix, questo
    era il modo più diretto per bypassare ogni controllo ed eseguire
    l'azione senza lasciare traccia coerente nel registro."""
    service, offer_repo = build_service_with_offer()
    with pytest.raises(HTTPException) as exc_info:
        run(
            service.execute_confirmed_action(
                FAKE_USER,
                {
                    "tool_name": "add_offer",
                    "resolved_input": {
                        "client_id": "c-1",
                        "mandante_id": "m-1",
                        "amount": 1500,
                    },
                },
            )
        )
    assert exc_info.value.status_code == 400
    assert len(offer_repo.docs) == 0


def test_log_id_inesistente_viene_rifiutato():
    service, offer_repo = build_service_with_offer()
    with pytest.raises(HTTPException) as exc_info:
        run(
            service.execute_confirmed_action(
                FAKE_USER,
                {
                    "tool_name": "add_offer",
                    "resolved_input": {
                        "client_id": "c-1",
                        "mandante_id": "m-1",
                        "amount": 1500,
                    },
                    "log_id": "log-che-non-esiste",
                },
            )
        )
    assert exc_info.value.status_code == 404
    assert len(offer_repo.docs) == 0


def test_log_di_un_altro_utente_viene_rifiutato():
    """Un log_id valido ma appartenente a un altro utente non deve mai
    permettere l'esecuzione (isolamento tra account)."""
    service, offer_repo = build_service_with_offer()
    log = run(
        service._log_action(
            "altro-utente",
            "chat",
            "registra vendita",
            "add_offer",
            {},
            status="in_attesa",
            resolved_params={"client_id": "c-1", "mandante_id": "m-1", "amount": 1500},
        )
    )
    with pytest.raises(HTTPException) as exc_info:
        run(
            service.execute_confirmed_action(
                FAKE_USER,
                {
                    "tool_name": "add_offer",
                    "resolved_input": log["resolved_params"],
                    "log_id": log["id"],
                },
            )
        )
    assert exc_info.value.status_code == 404
    assert len(offer_repo.docs) == 0


def test_tool_name_diverso_dal_log_viene_rifiutato():
    """Se il payload dichiara un tool diverso da quello registrato nel log
    (es. il client manda add_expense su un log_id di una add_offer), il
    servizio deve rifiutare invece di eseguire il tool 'sbagliato'."""
    service, offer_repo = build_service_with_offer()
    log = _prepare_pending_offer(service, offer_repo)
    with pytest.raises(HTTPException) as exc_info:
        run(
            service.execute_confirmed_action(
                FAKE_USER,
                {
                    "tool_name": "add_expense",
                    "resolved_input": {"amount": 50, "category": "carburante"},
                    "log_id": log["id"],
                },
            )
        )
    assert exc_info.value.status_code == 400
    assert len(offer_repo.docs) == 0
    # Il log resta 'in_attesa': la richiesta malformata non lo consuma.
    unchanged = next(d for d in service.action_log_repo.docs if d["id"] == log["id"])
    assert unchanged["status"] == "in_attesa"


def test_azione_gia_confermata_non_puo_essere_rieseguita():
    """Se lo stato è già 'confermata' (es. da una richiesta precedente ormai
    completata), un'ulteriore chiamata con lo stesso log_id va rifiutata."""
    service, offer_repo = build_service_with_offer()
    log = _prepare_pending_offer(service, offer_repo)
    run(
        service.action_log_repo.update_by_id(
            log["id"], FAKE_USER["id"], {"status": "confermata"}
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        run(
            service.execute_confirmed_action(
                FAKE_USER,
                {
                    "tool_name": "add_offer",
                    "resolved_input": log["resolved_params"],
                    "log_id": log["id"],
                },
            )
        )
    assert exc_info.value.status_code == 409
    assert len(offer_repo.docs) == 0


def test_azione_gia_annullata_non_puo_essere_eseguita():
    service, offer_repo = build_service_with_offer()
    log = _prepare_pending_offer(service, offer_repo)
    run(service.cancel_pending_action(FAKE_USER, log["id"]))

    with pytest.raises(HTTPException) as exc_info:
        run(
            service.execute_confirmed_action(
                FAKE_USER,
                {
                    "tool_name": "add_offer",
                    "resolved_input": log["resolved_params"],
                    "log_id": log["id"],
                },
            )
        )
    assert exc_info.value.status_code == 409
    assert len(offer_repo.docs) == 0


def test_doppio_annullamento_non_sovrascrive_unazione_gia_confermata():
    """Se l'azione è già stata confermata (scritta sul CRM) e per qualche
    motivo arriva anche una cancel-action per lo stesso log_id (tab
    duplicato, click residuo), l'annullamento non deve sovrascrivere lo
    stato reale 'confermata' con 'annullata'."""
    service, offer_repo = build_service_with_offer()
    log = _prepare_pending_offer(service, offer_repo)
    confirm_payload = {
        "tool_name": "add_offer",
        "resolved_input": log["resolved_params"],
        "log_id": log["id"],
    }
    with patch(
        "services.ai_service.actions.offers.order_service"
    ) as mock_order_service:
        mock_order_service.create_from_offer = AsyncMock(return_value={"total": 1500})
        run(service.execute_confirmed_action(FAKE_USER, confirm_payload))

    run(service.cancel_pending_action(FAKE_USER, log["id"]))

    final_log = next(d for d in service.action_log_repo.docs if d["id"] == log["id"])
    assert final_log["status"] == "confermata"  # non sovrascritto ad "annullata"
    assert len(offer_repo.docs) == 1


def test_tool_name_non_economico_viene_rifiutato():
    """execute_confirmed_action gestisce solo i tool economici con conferma
    (add_offer/add_expense); qualsiasi altro tool_name va rifiutato."""
    service, _ = build_service()
    with pytest.raises(HTTPException) as exc_info:
        run(
            service.execute_confirmed_action(
                FAKE_USER,
                {
                    "tool_name": "add_client",
                    "resolved_input": {"company_name": "Bar Rossi"},
                    "log_id": "qualsiasi",
                },
            )
        )
    assert exc_info.value.status_code == 400


if __name__ == "__main__":
    test_doppia_conferma_concorrente_scrive_una_sola_volta()
    print("OK: test 1 - doppia conferma non duplica")
    test_log_id_mancante_viene_rifiutato()
    print("OK: test 2 - log_id mancante rifiutato")
    test_log_id_inesistente_viene_rifiutato()
    print("OK: test 3 - log_id inesistente rifiutato")
    test_log_di_un_altro_utente_viene_rifiutato()
    print("OK: test 4 - isolamento tra utenti")
    test_tool_name_diverso_dal_log_viene_rifiutato()
    print("OK: test 5 - tool_name deve corrispondere al log")
    test_azione_gia_confermata_non_puo_essere_rieseguita()
    print("OK: test 6 - azione già confermata non rieseguibile")
    test_azione_gia_annullata_non_puo_essere_eseguita()
    print("OK: test 7 - azione già annullata non eseguibile")
    test_doppio_annullamento_non_sovrascrive_unazione_gia_confermata()
    print("OK: test 8 - cancel non sovrascrive conferma")
    test_tool_name_non_economico_viene_rifiutato()
    print("OK: test 9 - tool non economico rifiutato")
