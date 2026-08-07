import logging
from datetime import datetime, timedelta, timezone

from core.database import db
from services.storage_service import storage_delete

logger = logging.getLogger(__name__)

# Collection che ospitano documenti soft-deleted con lo stesso schema
# (is_deleted, deleted_at, storage_path): vedi document_repository.py e
# employee_document_repository.py.
TRASH_COLLECTIONS = ("documents", "employee_documents")


class DocumentTrashService:
    """Cancellazione fisica differita dei documenti eliminati dall'utente
    (DocumentService.delete_document / EmployeeDocumentService.delete_document):
    quelle chiamate fanno solo un soft-delete (is_deleted=True, deleted_at),
    così l'eliminazione risulta istantanea in UI e resta un margine contro un
    click accidentale — ma senza questo ciclo periodico il file su S3 non
    veniva MAI rimosso per un account normale (succedeva solo per
    cancellazione account GDPR o reset del demo condiviso), restando quindi
    occupato per sempre nello storage. Qui, dopo un periodo di
    conservazione, il file e il record vengono cancellati per davvero."""

    async def purge_expired(self, retention_days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        purged = 0
        for collection_name in TRASH_COLLECTIONS:
            collection = db[collection_name]
            docs = await collection.find(
                {"is_deleted": True, "deleted_at": {"$lt": cutoff}},
                {"_id": 0, "id": 1, "storage_path": 1},
            ).to_list(5000)
            if not docs:
                continue

            ids_to_delete = []
            for doc in docs:
                storage_path = doc.get("storage_path")
                if storage_path:
                    try:
                        storage_delete(storage_path)
                    except Exception as e:
                        # Non elimina il record se il file S3 non è stato
                        # rimosso: meglio ritentare al giro successivo che
                        # perdere il record e lasciare il file orfano per
                        # sempre (l'unico modo per ritrovarlo, a quel punto).
                        logger.warning(f"Pulizia cestino documenti: impossibile cancellare file S3 {storage_path}: {e}")
                        continue
                ids_to_delete.append(doc["id"])

            if ids_to_delete:
                result = await collection.delete_many({"id": {"$in": ids_to_delete}})
                purged += result.deleted_count

        return purged


document_trash_service = DocumentTrashService()
