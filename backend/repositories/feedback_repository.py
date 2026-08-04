from core.database import db


class FeedbackRepository:
    collection = db.feedback

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def find_many(self, limit: int = 500) -> list:
        return await self.collection.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)

    async def find_public(self, limit: int = 20) -> list:
        return await self.collection.find(
            {"approved": True, "publish_consent": True}, {"_id": 0}
        ).sort("created_at", -1).to_list(limit)

    async def find_one(self, fid: str):
        return await self.collection.find_one({"id": fid}, {"_id": 0})

    async def set_approved(self, fid: str, approved: bool) -> None:
        await self.collection.update_one({"id": fid}, {"$set": {"approved": approved}})

    async def delete(self, fid: str) -> None:
        await self.collection.delete_one({"id": fid})


feedback_repository = FeedbackRepository()
