from typing import Optional
from core.database import db


class AdminRepository:
    collection = db.users

    async def promote_by_email(self, email: str) -> bool:
        res = await self.collection.update_one({"email": email}, {"$set": {"role": "admin"}})
        return res.matched_count > 0

    async def count_agents(self, filters: Optional[dict] = None) -> int:
        query = {"role": "agent", **(filters or {})}
        return await self.collection.count_documents(query)

    async def find_agents(self, page: int, limit: int) -> list:
        skip = (page - 1) * limit
        return await self.collection.find(
            {"role": "agent"}, {"_id": 0, "password_hash": 0}
        ).sort("created_at", -1).skip(skip).to_list(limit)

    async def update_user(self, uid: str, data: dict) -> None:
        await self.collection.update_one({"id": uid}, {"$set": data})

    async def delete_user(self, uid: str) -> None:
        await self.collection.delete_one({"id": uid})


admin_repository = AdminRepository()
