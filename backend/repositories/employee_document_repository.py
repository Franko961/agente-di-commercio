from core.database import db
from core.utils import now_iso
from typing import Optional


class EmployeeDocumentRepository:
    collection = db.employee_documents

    async def find_many(self, employee_id: str, user_id: str) -> list:
        return await self.collection.find(
            {"employee_id": employee_id, "user_id": user_id, "is_deleted": {"$ne": True}}, {"_id": 0}
        ).sort("created_at", -1).to_list(500)

    async def find_one(self, did: str, user_id: str, employee_id: str) -> Optional[dict]:
        # Filtrato anche per employee_id, non solo did+user_id: il percorso
        # è /employees/{eid}/documents/{did}, quindi un id di documento
        # valido ma di un ALTRO dipendente dello stesso utente non deve
        # risolversi comunque solo perché eid nell'URL non viene controllato
        # — non è un salto tra utenti diversi (user_id resta filtrato), ma
        # un URL con eid "sbagliato" non deve comunque funzionare.
        return await self.collection.find_one(
            {"id": did, "user_id": user_id, "employee_id": employee_id, "is_deleted": {"$ne": True}}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update_meta(self, did: str, user_id: str, employee_id: str, data: dict) -> bool:
        res = await self.collection.update_one(
            {"id": did, "user_id": user_id, "employee_id": employee_id, "is_deleted": {"$ne": True}},
            {"$set": data},
        )
        return res.matched_count > 0

    async def soft_delete(self, did: str, user_id: str, employee_id: str) -> None:
        # Vedi commento in document_repository.soft_delete: deleted_at è
        # quello che serve al ciclo periodico di pulizia per applicare la
        # retention (services/document_trash_service.py).
        await self.collection.update_one(
            {"id": did, "user_id": user_id, "employee_id": employee_id},
            {"$set": {"is_deleted": True, "deleted_at": now_iso()}},
        )


employee_document_repository = EmployeeDocumentRepository()
