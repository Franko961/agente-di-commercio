from core.database import db


class LeaveRequestRepository:
    collection = db.leave_requests

    async def find_many(self, user_id: str, status: str = None) -> list:
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        return await self.collection.find(query, {"_id": 0}).sort("created_at", -1).to_list(2000)

    async def find_one(self, rid: str, user_id: str):
        return await self.collection.find_one({"id": rid, "user_id": user_id}, {"_id": 0})

    async def find_by_employee(self, employee_id: str) -> list:
        """Tutte le richieste (di ogni stato) di un singolo dipendente —
        usato per individuare invii duplicati e sovrapposizioni di date,
        indipendentemente dal tipo di assenza (es. ferie sovrapposte a
        una malattia)."""
        return await self.collection.find({"employee_id": employee_id}, {"_id": 0}).to_list(2000)

    async def find_overlapping(self, user_id: str, date_from: str, date_to: str, status: str = "approvata") -> list:
        """Richieste che si sovrappongono almeno in parte all'intervallo
        [date_from, date_to] (confronto su stringhe ISO YYYY-MM-DD, che
        ordina correttamente come farebbe un confronto di date) — usato
        dal calendario presenze per un dato mese."""
        return await self.collection.find({
            "user_id": user_id,
            "status": status,
            "date_from": {"$lte": date_to},
            "date_to": {"$gte": date_from},
        }, {"_id": 0}).to_list(2000)

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, rid: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one({"id": rid, "user_id": user_id}, {"$set": data})
        return res.matched_count > 0


leave_request_repository = LeaveRequestRepository()
