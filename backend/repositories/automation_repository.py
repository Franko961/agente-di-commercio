from core.database import db


class AutomationRepository:
    collection = db.automations

    async def find_many(self, user_id: str) -> list:
        return await self.collection.find({"user_id": user_id}, {"_id": 0}).to_list(500)

    async def find_all_enabled(self) -> list:
        """Usato dal motore di esecuzione (automation_engine): scorre le
        automazioni attive di TUTTI gli utenti, non solo di uno, a
        differenza di find_many che e' scoped per singolo utente per le
        rotte API."""
        return await self.collection.find({"enabled": True}, {"_id": 0}).to_list(5000)

    async def update_last_run(self, aid: str, data: dict) -> None:
        await self.collection.update_one({"id": aid}, {"$set": data})

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def insert_many(self, docs: list) -> None:
        if docs:
            await self.collection.insert_many(docs)

    async def update(self, aid: str, user_id: str, data: dict) -> None:
        await self.collection.update_one({"id": aid, "user_id": user_id}, {"$set": data})

    async def delete(self, aid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": aid, "user_id": user_id})


automation_repository = AutomationRepository()
