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


user_repository = UserRepository()
