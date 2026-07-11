from core.database import db


class MandanteRepository:
    collection = db.mandanti

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).to_list(500)

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, mid: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one({"id": mid, "user_id": user_id}, {"$set": data})
        return res.matched_count > 0

    async def delete(self, mid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": mid, "user_id": user_id})


mandante_repository = MandanteRepository()
