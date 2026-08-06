from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError, ValidationAppError
from repositories.employee_equipment_repository import employee_equipment_repository
from repositories.employee_repository import employee_repository


class EmployeeEquipmentService:
    def __init__(self, repo=employee_equipment_repository, employees=employee_repository):
        self.repo = repo
        self.employees = employees

    async def _validate_employee(self, user_id: str, employee_id: str) -> dict:
        employee = await self.employees.find_one(employee_id, user_id)
        if not employee:
            raise ValidationAppError("Dipendente non valido")
        return employee

    async def list_equipment(self, user: dict, employee_id: str) -> list:
        await self._validate_employee(user["id"], employee_id)
        return await self.repo.find_many(employee_id, user["id"])

    async def create_equipment(self, user: dict, employee_id: str, payload) -> dict:
        await self._validate_employee(user["id"], employee_id)
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            "employee_id": employee_id,
            "name": payload.name.strip(),
            "delivered_date": payload.delivered_date.isoformat() if payload.delivered_date else None,
            "returned_date": payload.returned_date.isoformat() if payload.returned_date else None,
            "status": payload.status,
            "notes": (payload.notes or "").strip(),
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_equipment(self, user: dict, eqid: str, payload) -> None:
        ok = await self.repo.update(eqid, user["id"], {
            "name": payload.name.strip(),
            "delivered_date": payload.delivered_date.isoformat() if payload.delivered_date else None,
            "returned_date": payload.returned_date.isoformat() if payload.returned_date else None,
            "status": payload.status,
            "notes": (payload.notes or "").strip(),
        })
        if not ok:
            raise NotFoundError("Dotazione non trovata")

    async def delete_equipment(self, user: dict, eqid: str) -> None:
        await self.repo.delete(eqid, user["id"])


employee_equipment_service = EmployeeEquipmentService()
