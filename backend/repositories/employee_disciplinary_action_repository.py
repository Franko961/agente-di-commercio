from core.database import db


class EmployeeDisciplinaryActionRepository:
    collection = db.disciplinary_actions

    async def find_many(self, employee_id: str, user_id: str) -> list:
        return await self.collection.find(
            {"employee_id": employee_id, "user_id": user_id}, {"_id": 0}
        ).sort("contestation_date", -1).to_list(500)

    # A differenza di employee_equipment_repository (find_one/update/delete
    # filtrati solo su id+user_id, senza employee_id), qui il record deve
    # appartenere anche all'{eid} indicato nell'URL — stesso principio già
    # corretto questa sessione per le sessioni presenze (vedi
    # attendance_repository.update/delete): altrimenti un id di record
    # valido per l'account ma passato con l'{eid} sbagliato avrebbe
    # comunque effetto.
    async def find_one(self, aid: str, user_id: str, employee_id: str):
        return await self.collection.find_one(
            {"id": aid, "user_id": user_id, "employee_id": employee_id}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(self, aid: str, user_id: str, employee_id: str, data: dict) -> bool:
        res = await self.collection.update_one(
            {"id": aid, "user_id": user_id, "employee_id": employee_id}, {"$set": data}
        )
        return res.matched_count > 0

    async def delete(self, aid: str, user_id: str, employee_id: str) -> None:
        await self.collection.delete_one({"id": aid, "user_id": user_id, "employee_id": employee_id})


employee_disciplinary_action_repository = EmployeeDisciplinaryActionRepository()
