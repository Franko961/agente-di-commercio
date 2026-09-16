from core.database import db


class PublicAiChatLogRepository:
    """Log anonimo delle domande fatte alla chat AI pubblica della homepage
    (nessun utente autenticato, nessuno storico per persona). Il documento
    salvato NON contiene l'IP del richiedente (quello resta solo, con TTL,
    nel rate limiter — vedi core/rate_limit.py) né altri identificatori:
    serve solo a Franco per vedere di cosa chiedono davvero i visitatori,
    non a collegare una conversazione a una persona."""

    collection = db.public_ai_chat_logs

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def find_many(self, limit: int = 200) -> list:
        return (
            await self.collection.find({}, {"_id": 0})
            .sort("created_at", -1)
            .to_list(limit)
        )


public_ai_chat_log_repository = PublicAiChatLogRepository()
