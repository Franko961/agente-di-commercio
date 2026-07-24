import asyncio
import logging

from core.database import db, close_db
from services.storage_service import init_storage

logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_SYNC_INTERVAL_SECONDS = 5 * 60

# Intervallo di controllo più breve della soglia di "bloccata" (5 minuti,
# vedi STUCK_EXECUTION_THRESHOLD_SECONDS in ai_service.py): un'azione bloccata
# viene quindi recuperata entro circa un minuto dal superamento della soglia,
# non solo al prossimo giro di sync di 5 minuti.
STUCK_AI_ACTION_CHECK_INTERVAL_SECONDS = 60

_gcal_sync_task = None
_stuck_ai_action_task = None


async def _google_calendar_sync_loop() -> None:
    from services.google_calendar_service import google_calendar_service
    while True:
        try:
            await asyncio.sleep(GOOGLE_CALENDAR_SYNC_INTERVAL_SECONDS)
            await google_calendar_service.sync_all_connected_accounts()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di sync Google Calendar fallito: {e}")


async def _stuck_ai_action_cleanup_loop() -> None:
    """Recupera periodicamente le azioni AI rimaste bloccate in
    'in_esecuzione' (tipicamente per un crash/riavvio del server a metà
    dell'esecuzione confermata di una vendita o di una spesa), segnandole
    'fallita' invece di lasciarle bloccate per sempre. Non riesegue mai
    l'azione: vedi AiService.reclaim_stuck_executions per i dettagli."""
    from services.ai_service import ai_service
    while True:
        try:
            await asyncio.sleep(STUCK_AI_ACTION_CHECK_INTERVAL_SECONDS)
            reclaimed = await ai_service.reclaim_stuck_executions()
            if reclaimed:
                logger.warning(
                    f"{reclaimed} azione/i AI bloccata/e in 'in_esecuzione' da "
                    "troppo tempo: segnata/e come 'fallita'."
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Ciclo di recupero azioni AI bloccate fallito: {e}")


async def run_startup() -> None:
    # Init object storage (non-blocking on failure)
    try:
        if init_storage():
            logger.info("Object storage initialized")
        else:
            logger.warning("Object storage NOT initialized — uploads will fail")
    except Exception as e:
        logger.error(f"Storage init error: {e}")

    await db.users.create_index("email", unique=True)
    await db.clients.create_index([("user_id", 1)])
    await db.offers.create_index([("user_id", 1)])
    await db.documents.create_index([("user_id", 1), ("is_deleted", 1)])
    # Queste cinque collection sono lette per intero ad ogni caricamento della
    # dashboard (get_stats/get_today_brief), filtrate per user_id: senza
    # indice, ogni query è una scansione completa della collection su TUTTI
    # gli utenti, non solo un filtro sull'utente corrente.
    await db.leads.create_index([("user_id", 1)])
    await db.appointments.create_index([("user_id", 1)])
    await db.commissions.create_index([("user_id", 1)])
    await db.expenses.create_index([("user_id", 1)])
    await db.orders.create_index([("user_id", 1)])
    # TTL: gli eventi di rate limiting più vecchi di 2 ore vengono eliminati
    # automaticamente da MongoDB (le finestre usate sono tutte <= 15 minuti).
    await db.rate_limit_events.create_index("created_at", expireAfterSeconds=7200)
    # Indice composto: find_many() filtra sempre per user_id e ordina per
    # created_at desc, quindi questo indice copre sia il filtro che il sort.
    await db.ai_action_logs.create_index([("user_id", 1), ("created_at", -1)])
    # Indice per il recupero periodico delle azioni bloccate in
    # 'in_esecuzione' (reclaim_stale_executions), che filtra su questi due
    # campi senza scoping per utente.
    await db.ai_action_logs.create_index([("status", 1), ("execution_started_at", 1)])

    global _gcal_sync_task, _stuck_ai_action_task
    _gcal_sync_task = asyncio.create_task(_google_calendar_sync_loop())
    _stuck_ai_action_task = asyncio.create_task(_stuck_ai_action_cleanup_loop())


async def run_shutdown() -> None:
    if _gcal_sync_task:
        _gcal_sync_task.cancel()
    if _stuck_ai_action_task:
        _stuck_ai_action_task.cancel()
    close_db()
