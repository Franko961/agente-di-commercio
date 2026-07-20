from core.database import db
from typing import Optional


class AiActionLogRepository:
    collection = db.ai_action_logs

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update_by_id(self, log_id: str, user_id: str, data: dict) -> None:
        await self.collection.update_one({"id": log_id, "user_id": user_id}, {"$set": data})

    async def transition(
        self, log_id: str, user_id: str, from_status: str, data: dict,
        extra_match: Optional[dict] = None,
    ) -> bool:
        """Aggiorna il log SOLO se si trova ancora in `from_status`, in
        un'unica operazione atomica lato MongoDB (compare-and-swap). Ritorna
        True se questa chiamata ha effettivamente eseguito la transizione,
        False se il log non esiste, non è dell'utente, non corrisponde a
        `extra_match`, o è già stato spostato da un'altra richiesta.

        Usato per impedire che un doppio clic, un retry di rete o una
        richiesta duplicata possano eseguire due volte la stessa azione
        economica (add_offer/add_expense) o annullare/confermare un'azione
        già elaborata: solo la prima richiesta "vince" la transizione."""
        query = {"id": log_id, "user_id": user_id, "status": from_status}
        if extra_match:
            query.update(extra_match)
        result = await self.collection.update_one(query, {"$set": data})
        return result.matched_count == 1

    async def find_many(
        self,
        user_id: str,
        tool_name: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 200,
    ) -> list:
        query = {"user_id": user_id}
        if tool_name:
            query["tool_name"] = tool_name
        if status:
            query["status"] = status
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query["$gte"] = date_from
            if date_to:
                # created_at è un timestamp ISO completo: includiamo tutta la
                # giornata di date_to, non solo l'istante 00:00:00.
                date_query["$lte"] = date_to + "T23:59:59.999999"
            query["created_at"] = date_query
        return await self.collection.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)

    async def find_one(self, log_id: str, user_id: str) -> Optional[dict]:
        return await self.collection.find_one({"id": log_id, "user_id": user_id}, {"_id": 0})


ai_action_log_repository = AiActionLogRepository()
