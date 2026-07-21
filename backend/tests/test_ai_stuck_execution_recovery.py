"""
Verifica il meccanismo di recupero delle azioni AI bloccate in
'in_esecuzione': se il server crasha esattamente tra la transizione atomica
'in_attesa' -> 'in_esecuzione' e il salvataggio del risultato finale, il
record resterebbe altrimenti bloccato per sempre in quello stato transitorio.

AiService.reclaim_stuck_executions() segna come 'fallita' ogni log rimasto
in 'in_esecuzione' da più di STUCK_EXECUTION_THRESHOLD_SECONDS, senza mai
rieseguire l'azione (potrebbe essere già stata scritta sul CRM prima del
crash).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_stuck_execution_recovery.py -v
"""
import sys
import asyncio
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from tests.test_ai_tool_forcing import build_service
from services.ai_service import STUCK_EXECUTION_THRESHOLD_SECONDS


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _iso(seconds_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()


def test_azione_bloccata_da_piu_della_soglia_viene_segnata_fallita():
    service, _ = build_service()
    run(service.action_log_repo.insert({
        "id": "stuck-1", "user_id": "user-1", "tool_name": "add_offer",
        "status": "in_esecuzione",
        "execution_started_at": _iso(STUCK_EXECUTION_THRESHOLD_SECONDS + 60),
    }))

    reclaimed = run(service.reclaim_stuck_executions())

    assert reclaimed == 1
    log = next(d for d in service.action_log_repo.docs if d["id"] == "stuck-1")
    assert log["status"] == "fallita"
    assert "riavvio" in log["result"].lower() or "interrotta" in log["result"].lower()


def test_azione_in_esecuzione_da_poco_non_viene_toccata():
    """Un'esecuzione genuinamente in corso (es. iniziata 2 secondi fa) non
    deve essere segnata come fallita: la soglia esiste apposta per
    distinguere un crash da un'esecuzione normale ancora in corso."""
    service, _ = build_service()
    run(service.action_log_repo.insert({
        "id": "fresh-1", "user_id": "user-1", "tool_name": "add_offer",
        "status": "in_esecuzione",
        "execution_started_at": _iso(2),
    }))

    reclaimed = run(service.reclaim_stuck_executions())

    assert reclaimed == 0
    log = next(d for d in service.action_log_repo.docs if d["id"] == "fresh-1")
    assert log["status"] == "in_esecuzione"


def test_azioni_in_altri_stati_non_vengono_toccate():
    service, _ = build_service()
    for status in ("in_attesa", "confermata", "annullata", "eseguita", "fallita"):
        run(service.action_log_repo.insert({
            "id": f"log-{status}", "user_id": "user-1", "tool_name": "add_offer",
            "status": status,
            "execution_started_at": _iso(STUCK_EXECUTION_THRESHOLD_SECONDS + 60),
        }))

    reclaimed = run(service.reclaim_stuck_executions())

    assert reclaimed == 0
    for status in ("in_attesa", "confermata", "annullata", "eseguita", "fallita"):
        log = next(d for d in service.action_log_repo.docs if d["id"] == f"log-{status}")
        assert log["status"] == status  # invariato


def test_execution_started_at_viene_impostato_alla_transizione():
    """execute_confirmed_action deve popolare execution_started_at nel
    momento in cui vince la transizione a 'in_esecuzione', non lasciarlo
    vuoto (altrimenti reclaim_stuck_executions non avrebbe nulla da
    confrontare con la soglia)."""
    from tests.test_ai_tool_forcing import build_service_with_offer

    service, offer_repo = build_service_with_offer()
    run(service.action_log_repo.insert({
        "id": "log-1", "user_id": "user-1", "tool_name": "add_offer", "status": "in_attesa",
        "resolved_params": {
            "client_id": "c-1", "client_name": "Rossi Srl", "mandante_id": "m-1",
            "mandante_name": "Paginesi", "title": "Vendita", "items": [],
            "amount": 500, "accepted": False, "sale_type": "nuovo",
        },
    }))

    run(service.execute_confirmed_action({"id": "user-1"}, {
        "tool_name": "add_offer",
        "resolved_input": {"amount": 500, "accepted": False, "sale_type": "nuovo"},
        "log_id": "log-1",
    }))

    log = next(d for d in service.action_log_repo.docs if d["id"] == "log-1")
    # A questo punto il log è già "confermata" (esecuzione completata), ma
    # deve comunque aver attraversato execution_started_at durante la
    # transizione: verifichiamo che il campo sia stato impostato e non sia
    # rimasto assente/None.
    assert log.get("execution_started_at") is not None


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
