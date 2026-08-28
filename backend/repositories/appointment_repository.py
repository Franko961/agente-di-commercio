from core.database import db


class AppointmentRepository:
    collection = db.appointments

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).to_list(
            2000
        )

    async def find_one(self, aid: str, user_id: str) -> dict:
        return await self.collection.find_one(
            {"id": aid, "user_id": user_id}, {"_id": 0}
        )

    async def find_by_google_event_id(self, user_id: str, google_event_id: str) -> dict:
        return await self.collection.find_one(
            {"user_id": user_id, "google_event_id": google_event_id}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def insert_many(self, docs: list) -> None:
        if docs:
            await self.collection.insert_many(docs)

    async def update(self, aid: str, user_id: str, data: dict) -> None:
        await self.collection.update_one(
            {"id": aid, "user_id": user_id}, {"$set": data}
        )

    async def delete(self, aid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": aid, "user_id": user_id})


appointment_repository = AppointmentRepository()
