from core.database import db


class VehicleDeadlineRepository:
    collection = db.vehicle_deadlines

    async def find_many(self, user_id: str) -> list:
        return (
            await self.collection.find({"user_id": user_id}, {"_id": 0})
            .sort("due_date", 1)
            .to_list(2000)
        )

    async def find_one(self, did: str, user_id: str):
        return await self.collection.find_one(
            {"id": did, "user_id": user_id}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, did: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one(
            {"id": did, "user_id": user_id}, {"$set": data}
        )
        return res.matched_count > 0

    async def delete(self, did: str, user_id: str) -> None:
        await self.collection.delete_one({"id": did, "user_id": user_id})


vehicle_deadline_repository = VehicleDeadlineRepository()
