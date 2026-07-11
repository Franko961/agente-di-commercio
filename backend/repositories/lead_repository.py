from core.database import db

class LeadRepository:
    collection = db.leads

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).to_list(2000)

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        return doc

    async def update(self, lid: str, user_id: str, data: dict) -> None:
        await self.collection.update_one({"id": lid, "user_id": user_id}, {"$set": data})

    async def update_status(self, lid: str, user_id: str, status: str) -> None:
        await self.collection.update_one({"id": lid, "user_id": user_id}, {"$set": {"status": status}})

    async def delete(self, lid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": lid, "user_id": user_id})


lead_repository = LeadRepository()
