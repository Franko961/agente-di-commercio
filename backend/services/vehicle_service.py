from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError, ValidationAppError
from repositories.vehicle_repository import vehicle_repository


class VehicleService:
    def __init__(self, repo=vehicle_repository):
        self.repo = repo

    async def list_vehicles(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_vehicle(self, user: dict, payload) -> dict:
        existing = await self.repo.find_by_plate(payload.plate, user["id"])
        if existing:
            raise ValidationAppError(f"Esiste già un mezzo con targa {payload.plate}")
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
        ok = await self.repo.update(vid, user["id"], payload.model_dump())
        if not ok:
            raise NotFoundError("Mezzo non trovato")

    async def set_active(self, user: dict, vid: str, active: bool) -> None:
        ok = await self.repo.update(vid, user["id"], {"active": active})
        if not ok:
            raise NotFoundError("Mezzo non trovato")

    async def delete_vehicle(self, user: dict, vid: str) -> None:
        await self.repo.delete(vid, user["id"])


vehicle_service = VehicleService()
