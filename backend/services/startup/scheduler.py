import asyncio
import logging

from core.database import close_db
from migrations.runner import apply_pending_migrations
from services.storage_service import init_storage

from .cleanup_jobs import (
    _cancel_finalize_loop,
    _contact_request_cleanup_loop,
    _demo_request_cleanup_loop,
    _demo_reset_loop,
    _document_trash_cleanup_loop,
    _stuck_ai_action_cleanup_loop,
)
from .indexes import create_indexes
from .monitoring_jobs import (
    _automation_engine_loop,
    _google_calendar_sync_loop,
    _health_alert_loop,
    _reconciliation_check_loop,
)

logger = logging.getLogger(__name__)

# Ognuno dei cicli sotto è protetto da job_lock_repository (vedi
# repositories/job_lock_repository.py) con una scadenza volutamente più
# breve del proprio intervallo: con più repliche Railway, solo l'istanza
# che vince il lock esegue il ciclo in quel giro; il lock scade comunque
# prima del giro successivo, così una qualunque replica (non
# necessariamente la stessa) può vincerlo la volta dopo. automation_engine
# fa eccezione: ha già una propria dedup più fine, per singola coppia
# automazione/target (vedi automation_run_repository.try_claim), quindi un
# lock a livello di intero ciclo non serve.
_gcal_sync_task = None
_stuck_ai_action_task = None
_health_alert_task = None
_automation_engine_task = None
_demo_reset_task = None
_cancel_finalize_task = None
_demo_request_cleanup_task = None
_contact_request_cleanup_task = None
_document_trash_cleanup_task = None
_reconciliation_check_task = None


async def run_startup() -> None:
    # Init object storage (non-blocking on failure)
    try:
        if init_storage():
            logger.info("Object storage initialized")
        else:
            logger.warning("Object storage NOT initialized — uploads will fail")
    except Exception as e:
        logger.error(f"Storage init error: {e}")

    await create_indexes()

    # Le migrazioni dati (backend/migrations/) girano dopo la creazione di
    # tutti gli indici (prima erano interlacciate a metà creazione indici,
    # per motivi di ordine storico nel vecchio startup_service.py
    # monolitico): nessuna dipende dall'esistenza di un indice per la
    # propria correttezza (sono update_many/update_one/find per _id, gli
    # indici influenzano solo le prestazioni delle query, non le scritture).
    # Tracciate in db.schema_migrations (vedi migrations/runner.py): a
    # differenza della creazione indici, ognuna gira una sola volta nella
    # vita del database, mai più ad ogni riavvio.
    await apply_pending_migrations()

    global _gcal_sync_task, _stuck_ai_action_task, _health_alert_task, _automation_engine_task, _demo_reset_task, _cancel_finalize_task, _demo_request_cleanup_task, _contact_request_cleanup_task, _document_trash_cleanup_task, _reconciliation_check_task
    _gcal_sync_task = asyncio.create_task(_google_calendar_sync_loop())
    _stuck_ai_action_task = asyncio.create_task(_stuck_ai_action_cleanup_loop())
    _health_alert_task = asyncio.create_task(_health_alert_loop())
    _automation_engine_task = asyncio.create_task(_automation_engine_loop())
    _demo_reset_task = asyncio.create_task(_demo_reset_loop())
    _cancel_finalize_task = asyncio.create_task(_cancel_finalize_loop())
    _demo_request_cleanup_task = asyncio.create_task(_demo_request_cleanup_loop())
    _contact_request_cleanup_task = asyncio.create_task(_contact_request_cleanup_loop())
    _document_trash_cleanup_task = asyncio.create_task(_document_trash_cleanup_loop())
    _reconciliation_check_task = asyncio.create_task(_reconciliation_check_loop())


async def run_shutdown() -> None:
    if _gcal_sync_task:
        _gcal_sync_task.cancel()
    if _stuck_ai_action_task:
        _stuck_ai_action_task.cancel()
    if _health_alert_task:
        _health_alert_task.cancel()
    if _automation_engine_task:
        _automation_engine_task.cancel()
    if _demo_reset_task:
        _demo_reset_task.cancel()
    if _cancel_finalize_task:
        _cancel_finalize_task.cancel()
    if _demo_request_cleanup_task:
        _demo_request_cleanup_task.cancel()
    if _contact_request_cleanup_task:
        _contact_request_cleanup_task.cancel()
    if _document_trash_cleanup_task:
        _document_trash_cleanup_task.cancel()
    if _reconciliation_check_task:
        _reconciliation_check_task.cancel()
    # PyMongo Async: close() è una coroutine (in Motor era sincrono).
    await close_db()
