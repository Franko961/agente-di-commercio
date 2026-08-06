from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError, ValidationAppError
from repositories.vehicle_repository import vehicle_repository
from repositories.employee_repository import employee_repository


class VehicleService:
    def __init__(self, repo=vehicle_repository, employees=employee_repository):
        self.repo = repo
        self.employees = employees

    async def list_vehicles(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def _validate_assigned_employee(self, user_id: str, employee_id) -> None:
        if employee_id and not await self.employees.find_one(employee_id, user_id):
            raise ValidationAppError("Dipendente non valido")

    async def create_vehicle(self, user: dict, payload) -> dict:
        existing = await self.repo.find_by_plate(payload.plate, user["id"])
        if existing:
            raise ValidationAppError(f"Esiste già un mezzo con targa {payload.plate}")
        await self._validate_assigned_employee(user["id"], payload.assigned_employee_id)
        doc = {
            "id": gen_id(), "user_id": user["id"],
            **payload.model_dump(),
            "active": True,
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_vehicle(self, user: dict, vid: str, payload) -> None:
        existing = await self.repo.find_by_plate(payload.plate, user["id"])
        if existing and existing["id"] != vid:
            raise ValidationAppError(f"Esiste già un mezzo con targa {payload.plate}")
        await self._validate_assigned_employee(user["id"], payload.assigned_employee_id)
        ok = await self.repo.update(vid, user["id"], payload.model_dump())
        if not ok:
            raise NotFoundError("Mezzo non trovato")

    async def set_active(self, user: dict, vid: str, active: bool) -> None:
        ok = await self.repo.update(vid, user["id"], {"active": active})
        if not ok:
            raise NotFoundError("Mezzo non trovato")

    async def delete_vehicle(self, user: dict, vid: str) -> None:
        await self.repo.delete(vid, user["id"])

    async def find_assigned(self, user: dict, employee_id: str):
        """Il mezzo (se esiste) assegnato a questo dipendente — per la tab
        "Mezzo assegnato" della scheda dipendente. None se il modulo
        Flotta non è in uso o nessun mezzo è collegato a lui."""
        vehicles = await self.repo.find_many(user["id"])
        return next((v for v in vehicles if v.get("assigned_employee_id") == employee_id), None)


vehicle_service = VehicleService()
