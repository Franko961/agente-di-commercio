from core.database import db
from typing import Optional

class ClientRepository:
    collection = db.clients

    async def find_many(self, user_id: str, filters: dict) -> list:
        query = {"user_id": user_id, **filters}
        return await self.collection.find(query, {"_id": 0}).to_list(2000)

    async def find_one(self, cid: str, user_id: str) -> Optional[dict]:
        return await self.collection.find_one({"id": cid, "user_id": user_id}, {"_id": 0})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        return doc

    async def update(self, cid: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one({"id": cid, "user_id": user_id}, {"$set": data})
        return res.matched_count > 0

    async def delete(self, cid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": cid, "user_id": user_id})


client_repository = ClientRepository()
