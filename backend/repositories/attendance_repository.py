from core.database import db
from typing import Optional


class AttendanceRepository:
    collection = db.attendance_sessions

    async def find_many(self, employee_id: str, user_id: str) -> list:
        return await self.collection.find(
            {"employee_id": employee_id, "user_id": user_id}, {"_id": 0}
        ).sort("clock_in", -1).to_list(2000)

    async def find_one(self, sid: str, user_id: str) -> Optional[dict]:
        return await self.collection.find_one({"id": sid, "user_id": user_id}, {"_id": 0})

    async def find_open_session(self, employee_id: str, user_id: str) -> Optional[dict]:
        """La sessione ancora aperta (clock_out assente) per questo
        dipendente, se esiste — al massimo una per volta: attendance_service
        rifiuta un secondo ingresso se ce n'è già una aperta, quindi questa
        query non ha mai più di un risultato in condizioni normali."""
        return await self.collection.find_one(
            {"employee_id": employee_id, "user_id": user_id, "clock_out": None}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, sid: str, user_id: str, data: dict) -> bool:
        res = await self.collection.update_one({"id": sid, "user_id": user_id}, {"$set": data})
        return res.matched_count > 0

    async def delete(self, sid: str, user_id: str) -> None:
        await self.collection.delete_one({"id": sid, "user_id": user_id})


attendance_repository = AttendanceRepository()
