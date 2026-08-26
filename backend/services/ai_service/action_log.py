import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from core.utils import gen_id, now_iso
from services.ai_service.catalog import STUCK_EXECUTION_THRESHOLD_SECONDS

logger = logging.getLogger(__name__)


async def log_action(
    action_log_repo, user_id: str, channel: str, raw_input: str, tool_name: str,
    proposed_params: dict, status: str, resolved_params: Optional[dict] = None,
    result: Optional[str] = None,
) -> dict:
    """Registra una voce nel registro azioni AI (audit log): chi (user_id),
    con cosa (comando testuale o trascritto dal canale voce/chat), quale
    tool, con quali parametri, ed esito. Non solleva mai: un errore nel
    logging non deve mai far fallire l'azione CRM vera e propria."""
    doc = {
        "id": gen_id(), "user_id": user_id,
        "channel": channel or "chat",
        "raw_input": raw_input or "",
        "tool_name": tool_name,
        "proposed_params": proposed_params or {},
        "resolved_params": resolved_params,
        "final_params": None,
        "status": status,
        "result": result,
        "created_at": now_iso(),
        "confirmed_at": None,
    }
    try:
        return await action_log_repo.insert(doc)
    except Exception as e:
        logger.error(f"AI action log insert error: {e}")
        return doc


async def cancel_pending_action(action_log_repo, user: dict, log_id: Optional[str]) -> dict:
    """Segna come annullata una voce 'in_attesa' del registro azioni,
    quando l'utente rifiuta la scheda di conferma senza registrare nulla.
    La transizione è atomica e condizionata allo stato attuale: se il log
    non è più 'in_attesa' (perché già confermato, annullato o in corso di
    esecuzione altrove) l'annullamento viene ignorato, così non si rischia
    di sovrascrivere l'esito reale di un'azione già elaborata."""
    if log_id:
        try:
            await action_log_repo.transition(
                log_id, user["id"], "in_attesa",
                {"status": "annullata", "confirmed_at": now_iso()},
            )
        except Exception as e:
            logger.error(f"AI action log cancel error: {e}")
    return {"ok": True}


async def list_actions(
    action_log_repo, user_id: str, tool_name: Optional[str] = None, status: Optional[str] = None,
    date_from: Optional[str] = None, date_to: Optional[str] = None, limit: int = 200,
) -> list:
    """Elenco filtrabile del registro azioni AI, per la pagina 'Registro AI'."""
    return await action_log_repo.find_many(
        user_id, tool_name=tool_name, status=status,
        date_from=date_from, date_to=date_to, limit=limit,
    )


async def reclaim_stuck_executions(action_log_repo) -> int:
    """Segna come 'fallita' le azioni rimaste bloccate in 'in_esecuzione'
    da più di STUCK_EXECUTION_THRESHOLD_SECONDS (vedi
    AiActionLogRepository.reclaim_stale_executions per il motivo:
    tipicamente un crash del server a metà dell'esecuzione confermata).
    Chiamato periodicamente da startup_service, non da una richiesta
    utente. Non riesegue mai l'azione: potrebbe essere già stata scritta
    sul CRM prima del crash."""
    threshold_iso = (
        datetime.now(timezone.utc) - timedelta(seconds=STUCK_EXECUTION_THRESHOLD_SECONDS)
    ).isoformat()
    return await action_log_repo.reclaim_stale_executions(
        threshold_iso,
        "Esecuzione interrotta (probabile riavvio del server): verificare "
        "manualmente se l'operazione è stata registrata prima di ripeterla.",
    )


async def list_pending_actions(action_log_repo, user_id: str, limit: int = 50) -> list:
    """Azioni economiche (add_offer, add_expense sopra soglia) proposte
    dall'AI e non ancora confermate né annullate, nel formato già atteso
    dal componente AIActionConfirm (tool_name, resolved_input, log_id).

    Serve a recuperare le schede di conferma quando l'utente chiude il
    pannello, ricarica la pagina, cambia schermata o riapre l'app: prima
    di questo endpoint le azioni 'in_attesa' esistevano solo nella
    risposta della singola chiamata a /chat che le aveva create, e
    andavano perse non appena lo stato locale del componente veniva
    azzerato (es. chiudendo il pannello vocale)."""
    logs = await action_log_repo.find_many(user_id, status="in_attesa", limit=limit)
    pending = []
    for log in logs:
        resolved = log.get("resolved_params")
        if not resolved:
            # Difesa in profondità: non dovrebbe succedere (un log
            # 'in_attesa' viene sempre creato con resolved_params), ma
            # se capitasse non mostriamo una scheda senza dati.
            continue
        pending.append({
            "log_id": log["id"],
            "tool_name": log["tool_name"],
            "resolved_input": resolved,
            "channel": log.get("channel", "chat"),
            "raw_input": log.get("raw_input", ""),
            "created_at": log.get("created_at"),
        })
    return pending
