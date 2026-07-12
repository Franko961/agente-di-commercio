from core.database import db
from typing import Optional


class UserRepository:
    collection = db.users

    async def find_by_email(self, email: str) -> Optional[dict]:
        return await self.collection.find_one({"email": email})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def find_by_id(self, uid: str) -> Optional[dict]:
        return await self.collection.find_one({"id": uid}, {"_id": 0, "password_hash": 0})

    async def update_by_id(self, uid: str, data: dict) -> None:
        await self.collection.update_one({"id": uid}, {"$set": data})

    async def update_by_stripe_subscription_id(self, sub_id: str, data: dict) -> None:
        await self.collection.update_one({"stripe_subscription_id": sub_id}, {"$set": data})


user_repository = UserRepository()
