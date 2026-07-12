import os
import logging

from core.database import db, close_db
from core.security import hash_password
from core.utils import gen_id, now_iso
from services.storage_service import init_storage
from services.seed_service import seed_service
from repositories.user_repository import user_repository

logger = logging.getLogger(__name__)


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

    # Seed admin/demo user — password e campi demo sono sempre risincronizzati
    # ad ogni avvio, così il login demo non si rompe mai anche se l'utente
    # esiste già nel DB da un deploy precedente.
    admin_email = os.environ.get("ADMIN_EMAIL", "agente@demo.it").lower()
    admin_pwd = os.environ.get("ADMIN_PASSWORD", "demo1234")
    demo_fields = {
        "password_hash": hash_password(admin_pwd),
        "plan": "pro",
        "subscription_status": "active",
        "is_demo": True,
    }
    existing = await user_repository.find_by_email(admin_email)
    if not existing:
        uid = gen_id()
        await user_repository.insert({
            "id": uid, "email": admin_email, "name": "Mario Bianchi",
            "role": "agent", "created_at": now_iso(),
            **demo_fields,
        })
        await seed_service.seed_demo(uid)
    else:
        await user_repository.update_by_id(existing["id"], demo_fields)
        await seed_service.seed_demo(existing["id"])


async def run_shutdown() -> None:
    close_db()
