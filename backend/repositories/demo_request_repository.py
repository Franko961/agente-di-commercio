from core.database import db


class DemoRequestRepository:
    collection = db.demo_requests

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def find_many(self, limit: int = 500) -> list:
        return await self.collection.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)

    async def find_by_email(self, email: str):
        return await self.collection.find_one({"email": email}, {"_id": 0})

    async def delete_older_than(self, cutoff_iso: str) -> int:
        """created_at è salvato come stringa ISO (now_iso()), non una data
        BSON nativa: un indice TTL nativo non è applicabile qui, va ripulito
        con un confronto testuale (che per il formato ISO 8601 UTC ordina
        correttamente come farebbe un confronto di date)."""
        result = await self.collection.delete_many({"created_at": {"$lt": cutoff_iso}})
        return result.deleted_count


demo_request_repository = DemoRequestRepository()
