from core.database import db
from typing import Optional


class AiActionLogRepository:
    collection = db.ai_action_logs

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update_by_id(self, log_id: str, user_id: str, data: dict) -> None:
        await self.collection.update_one({"id": log_id, "user_id": user_id}, {"$set": data})

    async def find_many(
        self,
        user_id: str,
        tool_name: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 200,
    ) -> list:
        query = {"user_id": user_id}
        if tool_name:
            query["tool_name"] = tool_name
        if status:
            query["status"] = status
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                # created_at è un timestamp ISO completo: includiamo tutta la
                # giornata di date_to, non solo l'istante 00:00:00.
                date_query["$lte"] = date_to + "T23:59:59.999999"
            query["created_at"] = date_query
        return await self.collection.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)

    async def find_one(self, log_id: str, user_id: str) -> Optional[dict]:
        return await self.collection.find_one({"id": log_id, "user_id": user_id}, {"_id": 0})


ai_action_log_repository = AiActionLogRepository()
