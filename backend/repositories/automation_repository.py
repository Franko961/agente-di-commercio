from core.database import db


class AutomationRepository:
    collection = db.automations

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).to_list(500)

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, aid: str, user_id: str, data: dict) -> None:
        await self.collection.update_one({"id": aid, "user_id": user_id}, {"$set": data})

    async def delete(self, aid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": aid, "user_id": user_id})


automation_repository = AutomationRepository()
