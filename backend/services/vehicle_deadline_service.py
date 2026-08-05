from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError, ValidationAppError
from repositories.vehicle_deadline_repository import vehicle_deadline_repository
from repositories.vehicle_repository import vehicle_repository


class VehicleDeadlineService:
    def __init__(self, repo=vehicle_deadline_repository, vehicles=vehicle_repository):
        self.repo = repo
        self.vehicles = vehicles

    async def list_deadlines(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_deadline(self, user: dict, payload) -> dict:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            "vehicle_id": payload.vehicle_id,
            # Denormalizzato apposta: se il mezzo viene poi eliminato, la
            # scadenza resta leggibile nello storico invece di mostrare un
            # riferimento orfano (stesso principio di employee_name in
            # leave_request_service.py).
            "vehicle_plate": vehicle["plate"],
            "type": payload.type,
            "due_date": payload.due_date.isoformat(),
            "note": (payload.note or "").strip(),
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_deadline(self, user: dict, did: str, payload) -> None:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        ok = await self.repo.update(did, user["id"], {
            "vehicle_id": payload.vehicle_id,
            "vehicle_plate": vehicle["plate"],
            "type": payload.type,
            "due_date": payload.due_date.isoformat(),
            "note": (payload.note or "").strip(),
        })
        if not ok:
            raise NotFoundError("Scadenza non trovata")

    async def delete_deadline(self, user: dict, did: str) -> None:
        await self.repo.delete(did, user["id"])


vehicle_deadline_service = VehicleDeadlineService()
