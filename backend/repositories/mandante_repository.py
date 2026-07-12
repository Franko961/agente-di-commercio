from core.database import db


class MandanteRepository:
    collection = db.mandanti

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).to_list(500)

    async def count(self, user_id: str) -> int:
        return await self.collection.count_documents({"user_id": user_id})

    async def find_one(self, mid: str, user_id: str):
        return await self.collection.find_one({"id": mid, "user_id": user_id}, {"_id": 0})

    async def find_by_name_regex(self, user_id: str, name: str):
        return await self.collection.find_one(
            {"user_id": user_id, "name": {"$regex": name, "$options": "i"}},
            {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def insert_many(self, docs: list) -> None:
        if docs:
            await self.collection.insert_many(docs)

    async def update(self, mid: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one({"id": mid, "user_id": user_id}, {"$set": data})
        return res.matched_count > 0

    async def delete(self, mid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": mid, "user_id": user_id})


mandante_repository = MandanteRepository()
