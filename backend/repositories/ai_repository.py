from core.database import db


class AiRepository:
    collection = db.ai_logs

    async def find_history(self, user_id: str, limit: int = 30) -> list:
        return (
            await self.collection.find({"user_id": user_id}, {"_id": 0})
            .sort("created_at", 1)
            .to_list(limit)
        )

    async def find_recent_for_context(self, user_id: str, limit: int = 10) -> list:
        """Ultimi N scambi in ordine cronologico crescente, per costruire i messages dell'API."""
        logs = (
            await self.collection.find({"user_id": user_id}, {"_id": 0})
            .sort("created_at", -1)
            .to_list(limit)
        )
        logs.reverse()
        return logs

    async def count_since(self, user_id: str, since_iso: str) -> int:
        """Conta i messaggi di user_id con created_at >= since_iso (UTC), usato
        per applicare il limite mensile di messaggi AI del piano."""
        return await self.collection.count_documents(
            {
                "user_id": user_id,
                "created_at": {"$gte": since_iso},
            }
        )

    async def insert_log(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def delete_all(self, user_id: str) -> None:
        await self.collection.delete_many({"user_id": user_id})


ai_repository = AiRepository()
