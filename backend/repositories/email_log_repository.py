from core.database import db


class EmailLogRepository:
    collection = db.email_logs

    async def find_many(self, user_id: str) -> list:
        return (
            await self.collection.find({"user_id": user_id}, {"_id": 0})
            .sort("created_at", -1)
            .to_list(200)
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc


email_log_repository = EmailLogRepository()
