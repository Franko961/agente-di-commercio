from core.database import db


class EmployeeEquipmentRepository:
    collection = db.employee_equipment

    async def find_many(self, employee_id: str, user_id: str) -> list:
        return (
            await self.collection.find(
                {"employee_id": employee_id, "user_id": user_id}, {"_id": 0}
            )
            .sort("created_at", -1)
            .to_list(500)
        )

    # find_one/update/delete filtrano anche per employee_id (non solo
    # id+user_id): un id di record valido per l'account ma riferito con
    # l'employee_id sbagliato nell'URL non deve avere effetto — stesso
    # principio già corretto per le sessioni presenze (commit e3de79b) e
    # per le Contestazioni disciplinari (employee_disciplinary_action_repository.py).
    async def find_one(self, eqid: str, user_id: str, employee_id: str):
        return await self.collection.find_one(
            {"id": eqid, "user_id": user_id, "employee_id": employee_id}, {"_id": 0}
        )

    async def insert(self, doc: dict) -> dict:
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def update(
        self, eqid: str, user_id: str, employee_id: str, data: dict
    ) -> bool:
        res = await self.collection.update_one(
            {"id": eqid, "user_id": user_id, "employee_id": employee_id}, {"$set": data}
        )
        return res.matched_count > 0

    async def delete(self, eqid: str, user_id: str, employee_id: str) -> None:
        await self.collection.delete_one(
            {"id": eqid, "user_id": user_id, "employee_id": employee_id}
        )


employee_equipment_repository = EmployeeEquipmentRepository()
