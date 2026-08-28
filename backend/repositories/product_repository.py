from typing import Optional

from core.database import db


class ProductRepository:
    collection = db.products

    async def find_many(self, user_id: str, mandante_id: Optional[str] = None) -> list:
        query = {"user_id": user_id}
        if mandante_id:
            query["mandante_id"] = mandante_id
        return await self.collection.find(query, {"_id": 0}).to_list(1000)

    async def find_by_name_regex(
        self, user_id: str, mandante_id: str, name: str
    ) -> Optional[dict]:
        return await self.collection.find_one(
            {
                "user_id": user_id,
                "mandante_id": mandante_id,
                "name": {"$regex": name, "$options": "i"},
            },
            {"_id": 0},
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def insert_many(self, docs: list) -> None:
        if docs:
            await self.collection.insert_many(docs)

    async def update(self, pid: str, user_id: str, data: dict) -> None:
        await self.collection.update_one(
            {"id": pid, "user_id": user_id}, {"$set": data}
        )

    async def delete(self, pid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": pid, "user_id": user_id})


product_repository = ProductRepository()
