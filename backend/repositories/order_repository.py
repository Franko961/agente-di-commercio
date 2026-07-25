from pymongo import ReturnDocument
from core.database import db


class OrderRepository:
    collection = db.orders

    async def find_many(self, user_id: str, mandante_id: str = None) -> list:
        query = {"user_id": user_id}
        if mandante_id:
            query["mandante_id"] = mandante_id
        return await self.collection.find(query, {"_id": 0}).to_list(2000)

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

    async def update(self, oid: str, user_id: str, data: dict) -> None:
        """Sostituzione completa dei campi modificabili (righe, prezzi,
        mandante, ecc.), stesso pattern usato da offer_repository.update."""
        await self.collection.update_one({"id": oid, "user_id": user_id}, {"$set": data})

    async def update_fields(self, oid: str, user_id: str, data: dict) -> bool:
        """Aggiornamento parziale (solo i campi presenti in data): usato per
        stato/evasione/pagamento senza toccare righe e prezzi. Restituisce
        True se un documento è stato trovato e aggiornato."""
        res = await self.collection.update_one({"id": oid, "user_id": user_id}, {"$set": data})
        return res.matched_count > 0

    async def delete(self, oid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": oid, "user_id": user_id})

    async def next_order_number(self, user_id: str) -> str:
        """Genera un numero ordine progressivo per utente (es. 'ORD-0007'),
        incrementato in modo atomico tramite find_one_and_update — evita la
        race condition di due ordini creati nello stesso istante che
        otterrebbero lo stesso numero se contassimo semplicemente i
        documenti esistenti."""
        counter = await db.counters.find_one_and_update(
            {"_id": f"order_number:{user_id}"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return f"ORD-{counter['seq']:04d}"


order_repository = OrderRepository()
