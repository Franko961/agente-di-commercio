from typing import Optional

from core.database import db
from core.utils import now_iso


class DocumentRepository:
    collection = db.documents

    async def find_many(self, user_id: str) -> list:
        return (
            await self.collection.find(
                {"user_id": user_id, "is_deleted": {"$ne": True}}, {"_id": 0}
            )
            .sort("created_at", -1)
            .to_list(2000)
        )

    async def find_one(
        self, did: str, user_id: str, include_deleted: bool = False
    ) -> Optional[dict]:
        query: dict = {"id": did, "user_id": user_id}
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}
        return await self.collection.find_one(query, {"_id": 0})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def insert_many(self, docs: list) -> None:
        if docs:
            await self.collection.insert_many(docs)

    async def update_meta(self, did: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one(
            {"id": did, "user_id": user_id, "is_deleted": {"$ne": True}},
            {"$set": data},
        )
        return res.matched_count > 0

    async def soft_delete(self, did: str, user_id: str) -> None:
        # deleted_at (non solo is_deleted) è quello che permette al ciclo
        # periodico di pulizia (services/document_trash_service.py) di sapere
        # QUANDO è stato eliminato, per applicare la retention — senza,
        # servirebbe rifarsi a created_at (la data di caricamento, non di
        # eliminazione), sballando la finestra di conservazione.
        await self.collection.update_one(
            {"id": did, "user_id": user_id},
            {"$set": {"is_deleted": True, "deleted_at": now_iso()}},
        )


document_repository = DocumentRepository()
