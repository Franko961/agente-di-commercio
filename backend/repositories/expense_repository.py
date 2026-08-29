from typing import Optional

from core.database import db


class ExpenseRepository:
    collection = db.expenses

    async def find_many(
        self,
        user_id: str,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list:
        query: dict = {"user_id": user_id}
        if category:
            query["category"] = category
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                date_query["$lte"] = date_to
            query["date"] = date_query
        return (
            await self.collection.find(query, {"_id": 0}).sort("date", -1).to_list(2000)
        )

    async def find_one(self, eid: str, user_id: str) -> Optional[dict]:
        return await self.collection.find_one(
            {"id": eid, "user_id": user_id}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, eid: str, user_id: str, data: dict) -> None:
        await self.collection.update_one(
            {"id": eid, "user_id": user_id}, {"$set": data}
        )

    async def delete(self, eid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": eid, "user_id": user_id})


expense_repository = ExpenseRepository()
