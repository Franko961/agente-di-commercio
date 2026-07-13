from typing import Optional
from core.database import db


class GoogleCalendarRepository:
    collection = db.google_calendar_connections

    async def find_by_user(self, user_id: str) -> Optional[dict]:
        return await self.collection.find_one({"user_id": user_id}, {"_id": 0})

    async def upsert(self, user_id: str, data: dict) -> None:
        await self.collection.update_one(
            {"user_id": user_id}, {"$set": data}, upsert=True
        )

    async def delete(self, user_id: str) -> None:
        await self.collection.delete_one({"user_id": user_id})

    async def find_all(self) -> list:
        """Tutte le connessioni attive, usato dal job di polling periodico."""
        return await self.collection.find({}, {"_id": 0}).to_list(10_000)


google_calendar_repository = GoogleCalendarRepository()
