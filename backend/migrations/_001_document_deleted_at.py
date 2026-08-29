"""Migrazione una tantum: i documenti già soft-deleted PRIMA dell'introduzione
del campo deleted_at (soft_delete si limitava a is_deleted=True) non hanno mai
avuto quel campo — senza backfill, il filtro deleted_at < cutoff del ciclo di
pulizia (services.startup.cleanup_jobs._document_trash_cleanup_loop) non li
troverebbe mai, restando orfani per sempre esattamente come il problema che il
ciclo risolve. Il valore di backfill è 'adesso', non una data nel passato: dà
a questi documenti l'intera finestra di conservazione invece di cancellarli in
blocco al primo giro utile dopo il deploy."""

from datetime import datetime, timezone

from core.database import db


async def run() -> None:
    now = datetime.now(timezone.utc).isoformat()
    for collection_name in ("documents", "employee_documents"):
        await db[collection_name].update_many(
            {"is_deleted": True, "deleted_at": {"$exists": False}},
            {"$set": {"deleted_at": now}},
        )
