from core.database import db


class OrderRepository:
    collection = db.orders

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).to_list(2000)

    async def find_by_client(self, user_id: str, client_id: str) -> list:
        return await self.collection.find({"user_id": user_id, "client_id": client_id}, {"_id": 0}).to_list(2000)

    async def find_by_source_offer(self, offer_id: str, user_id: str):
        return await self.collection.find_one({"source_offer_id": offer_id, "user_id": user_id}, {"_id": 0})

    async def find_one(self, oid: str, user_id: str):
        return await self.collection.find_one({"id": oid, "user_id": user_id}, {"_id": 0})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def delete(self, oid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": oid, "user_id": user_id})


order_repository = OrderRepository()
