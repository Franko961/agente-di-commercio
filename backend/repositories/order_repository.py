from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from core.database import db
from core.exceptions import ConflictError


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
        # L'indice univoco su (user_id, numero_ordine) — vedi
        # startup_service.run_startup — è l'ultima linea di difesa contro i
        # duplicati: next_order_number() è atomico e non collide mai da
        # solo, ma numero_ordine resta un campo modificabile a mano da form
        # (creazione/modifica), quindi un valore digitato dall'utente
        # potrebbe collidere con uno già esistente (proprio o generato).
        try:
            await self.collection.insert_one(doc)
        except DuplicateKeyError as e:
            # Distingue quale dei due indici univoci ha bloccato l'insert
            # (vedi startup_service.run_startup): stesso doc, due possibili
            # collisioni con causa e messaggio diversi.
            key_pattern = (e.details or {}).get("keyPattern", {})
            if "source_offer_id" in key_pattern:
                raise ConflictError("Esiste già un ordine creato da questa offerta")
            raise ConflictError(f"Numero ordine \"{doc.get('numero_ordine')}\" già in uso")
        doc.pop("_id", None)
        return doc

    async def update(self, oid: str, user_id: str, data: dict) -> None:
        """Sostituzione completa dei campi modificabili (righe, prezzi,
        mandante, ecc.), stesso pattern usato da offer_repository.update."""
        try:
            await self.collection.update_one({"id": oid, "user_id": user_id}, {"$set": data})
        except DuplicateKeyError:
            raise ConflictError(f"Numero ordine \"{data.get('numero_ordine')}\" già in uso")

    async def update_fields(self, oid: str, user_id: str, data: dict) -> bool:
        """Aggiornamento parziale (solo i campi presenti in data): usato per
        stato/evasione/pagamento senza toccare righe e prezzi. Restituisce
        True se un documento è stato trovato e aggiornato."""
        try:
            res = await self.collection.update_one({"id": oid, "user_id": user_id}, {"$set": data})
        except DuplicateKeyError:
            raise ConflictError(f"Numero ordine \"{data.get('numero_ordine')}\" già in uso")
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
