from core.database import db


class CargoLoadRepository:
    collection = db.cargo_loads

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).sort("date", -1).to_list(2000)

    async def find_one(self, lid: str, user_id: str):
        return await self.collection.find_one({"id": lid, "user_id": user_id}, {"_id": 0})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, lid: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one({"id": lid, "user_id": user_id}, {"$set": data})
        return res.matched_count > 0

    async def sign(self, lid: str, user_id: str, signature: str, signer_name: str, signed_at: str) -> bool:
        res = await self.collection.update_one(
            {"id": lid, "user_id": user_id},
            {"$set": {
                "signature": signature,
                "signer_name": signer_name,
                "signed_at": signed_at,
                "status": "consegnato",
            }}
        )
        return res.matched_count > 0

    async def delete(self, lid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": lid, "user_id": user_id})


cargo_load_repository = CargoLoadRepository()
