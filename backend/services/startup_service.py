import asyncio
import logging

from core.database import db, close_db
from services.storage_service import init_storage

logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_SYNC_INTERVAL_SECONDS = 5 * 60

_gcal_sync_task = None


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
    # TTL: gli eventi di rate limiting più vecchi di 2 ore vengono eliminati
    # automaticamente da MongoDB (le finestre usate sono tutte <= 15 minuti).
    await db.rate_limit_events.create_index("created_at", expireAfterSeconds=7200)

    global _gcal_sync_task
    _gcal_sync_task = asyncio.create_task(_google_calendar_sync_loop())


async def run_shutdown() -> None:
    if _gcal_sync_task:
        _gcal_sync_task.cancel()
    close_db()
