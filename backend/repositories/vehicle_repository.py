from core.database import db


class VehicleRepository:
    collection = db.vehicles

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).sort("plate", 1).to_list(1000)

    async def find_one(self, vid: str, user_id: str):
        return await self.collection.find_one({"id": vid, "user_id": user_id}, {"_id": 0})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, vid: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one({"id": vid, "user_id": user_id}, {"$set": data})
        return res.matched_count > 0

    async def delete(self, vid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": vid, "user_id": user_id})


vehicle_repository = VehicleRepository()
