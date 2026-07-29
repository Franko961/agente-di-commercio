from core.database import db


class ContactRequestRepository:
    collection = db.contact_requests

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def find_many(self, limit: int = 500) -> list:
        return await self.collection.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)


contact_request_repository = ContactRequestRepository()
