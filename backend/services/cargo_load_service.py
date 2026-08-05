from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError, ValidationAppError
from repositories.cargo_load_repository import cargo_load_repository
from repositories.vehicle_repository import vehicle_repository


class CargoLoadService:
    def __init__(self, repo=cargo_load_repository, vehicles=vehicle_repository):
        self.repo = repo
        self.vehicles = vehicles

    async def list_loads(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_load(self, user: dict, payload) -> dict:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            "vehicle_id": payload.vehicle_id,
            "vehicle_plate": vehicle["plate"],
            "date": payload.date.isoformat(),
            "description": payload.description.strip(),
            "destination": (payload.destination or "").strip(),
            "notes": (payload.notes or "").strip(),
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_load(self, user: dict, lid: str, payload) -> None:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        ok = await self.repo.update(lid, user["id"], {
            "vehicle_id": payload.vehicle_id,
            "vehicle_plate": vehicle["plate"],
            "date": payload.date.isoformat(),
            "description": payload.description.strip(),
            "destination": (payload.destination or "").strip(),
            "notes": (payload.notes or "").strip(),
        })
        if not ok:
            raise NotFoundError("Carico non trovato")

    async def delete_load(self, user: dict, lid: str) -> None:
        await self.repo.delete(lid, user["id"])


cargo_load_service = CargoLoadService()
