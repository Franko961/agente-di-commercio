from typing import Optional

from core.database import db


class OfferRepository:
    collection = db.offers

    async def find_many(self, user_id: str, mandante_id: Optional[str] = None) -> list:
        query = {"user_id": user_id}
        if mandante_id:
            query["mandante_id"] = mandante_id
        return await self.collection.find(query, {"_id": 0}).to_list(2000)

    async def find_one(self, oid: str, user_id: str):
        return await self.collection.find_one(
            {"id": oid, "user_id": user_id}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def insert_many(self, docs: list) -> None:
        if docs:
            await self.collection.insert_many(docs)

    async def update(self, oid: str, user_id: str, data: dict) -> None:
        await self.collection.update_one(
            {"id": oid, "user_id": user_id}, {"$set": data}
        )

    async def update_status(self, oid: str, user_id: str, status: str) -> None:
        await self.collection.update_one(
            {"id": oid, "user_id": user_id}, {"$set": {"status": status}}
        )

    async def sign(
        self, oid: str, user_id: str, signature: str, signer_name: str, signed_at: str
    ) -> bool:
        res = await self.collection.update_one(
            {"id": oid, "user_id": user_id},
            {
                "$set": {
                    "signature": signature,
                    "signer_name": signer_name,
                    "signed_at": signed_at,
                    "status": "accettata",
                }
            },
        )
        return res.matched_count > 0

    async def delete(self, oid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": oid, "user_id": user_id})


offer_repository = OfferRepository()
