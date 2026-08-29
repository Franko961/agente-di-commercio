from core.database import db


class VehicleCostRepository:
    collection = db.vehicle_costs

    async def find_many(self, user_id: str) -> list:
        return (
            await self.collection.find({"user_id": user_id}, {"_id": 0})
            .sort("date", -1)
            .to_list(2000)
        )

    async def find_one(self, cid: str, user_id: str):
        return await self.collection.find_one(
            {"id": cid, "user_id": user_id}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, cid: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one(
            {"id": cid, "user_id": user_id}, {"$set": data}
        )
        return res.matched_count > 0

    async def delete(self, cid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": cid, "user_id": user_id})


vehicle_cost_repository = VehicleCostRepository()
