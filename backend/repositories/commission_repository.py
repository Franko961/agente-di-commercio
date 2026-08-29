from typing import Optional

from core.database import db


class CommissionRepository:
    collection = db.commissions

    async def find_many(self, user_id: str, mandante_id: Optional[str] = None) -> list:
        query = {"user_id": user_id}
        if mandante_id:
            query["mandante_id"] = mandante_id
        return await self.collection.find(query, {"_id": 0}).to_list(2000)

    async def find_one(self, cid: str, user_id: str):
        return await self.collection.find_one(
            {"id": cid, "user_id": user_id}, {"_id": 0}
        )

    async def find_by_offer(self, offer_id: str, user_id: str):
        return await self.collection.find_one(
            {"offer_id": offer_id, "user_id": user_id}
        )

    async def find_by_order(self, order_id: str, user_id: str) -> list:
        return await self.collection.find(
            {"order_id": order_id, "user_id": user_id}, {"_id": 0}
        ).to_list(50)

    async def delete_by_order(self, order_id: str, user_id: str) -> None:
        await self.collection.delete_many({"order_id": order_id, "user_id": user_id})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def insert_many(self, docs: list) -> None:
        if docs:
            await self.collection.insert_many(docs)

    async def update_status(self, cid: str, user_id: str, status: str) -> None:
        await self.collection.update_one(
            {"id": cid, "user_id": user_id}, {"$set": {"status": status}}
        )

    async def delete(self, cid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": cid, "user_id": user_id})


commission_repository = CommissionRepository()
