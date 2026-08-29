from datetime import datetime, timezone

from core.database import db
from core.utils import gen_id


async def backfill_manual_commission_ids() -> None:
    """Migrazione una tantum (query mirata, no-op sui giri successivi una
    volta completata): i documenti creati PRIMA dell'introduzione del CRUD
    per id — quando l'upsert era per (user_id, period), vedi il vecchio
    manual_commission_repository.py — non hanno mai avuto un campo id. Ora
    che l'unicità su (user_id, period) viene tolta (vedi
    services.startup.indexes.create_indexes), due righe senza id potrebbero
    finire a condividere lo stesso fallback sintetico in
    commission_service.normalize_manual_commission (f"manual:{period}"),
    una collisione prima impossibile perché l'indice univoco garantiva un
    solo documento per mese. Backfillare qui un id reale su ogni documento
    esistente chiude il problema alla radice."""
    async for doc in db.manual_commissions.find({"id": {"$exists": False}}, {"_id": 1}):
        await db.manual_commissions.update_one(
            {"_id": doc["_id"]}, {"$set": {"id": gen_id()}}
        )


async def backfill_document_deleted_at() -> None:
    """Migrazione una tantum (no-op sui giri successivi una volta
    completata): i documenti già soft-deleted PRIMA dell'introduzione del
    campo deleted_at (soft_delete si limitava a is_deleted=True) non hanno
    mai avuto quel campo — senza backfill, il filtro deleted_at < cutoff del
    ciclo di pulizia (services.startup.cleanup_jobs._document_trash_cleanup_loop)
    non li troverebbe mai, restando orfani per sempre esattamente come il
    problema che il ciclo risolve. Il valore di backfill è 'adesso', non una
    data nel passato: dà a questi documenti l'intera finestra di
    conservazione invece di cancellarli in blocco al primo giro utile dopo
    il deploy."""
    now = datetime.now(timezone.utc).isoformat()
    for collection_name in ("documents", "employee_documents"):
        await db[collection_name].update_many(
            {"is_deleted": True, "deleted_at": {"$exists": False}},
            {"$set": {"deleted_at": now}},
        )
