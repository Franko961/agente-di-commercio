from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError, ValidationAppError
from repositories.vehicle_cost_repository import vehicle_cost_repository
from repositories.vehicle_repository import vehicle_repository


class VehicleCostService:
    def __init__(self, repo=vehicle_cost_repository, vehicles=vehicle_repository):
        self.repo = repo
        self.vehicles = vehicles

    async def list_costs(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_cost(self, user: dict, payload) -> dict:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            "vehicle_id": payload.vehicle_id,
            "vehicle_plate": vehicle["plate"],
            "category": payload.category,
            "amount": payload.amount,
            "date": payload.date.isoformat(),
            "description": (payload.description or "").strip(),
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_cost(self, user: dict, cid: str, payload) -> None:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        ok = await self.repo.update(cid, user["id"], {
            "vehicle_id": payload.vehicle_id,
            "vehicle_plate": vehicle["plate"],
            "category": payload.category,
            "amount": payload.amount,
            "date": payload.date.isoformat(),
            "description": (payload.description or "").strip(),
        })
        if not ok:
            raise NotFoundError("Costo non trovato")

    async def delete_cost(self, user: dict, cid: str) -> None:
        await self.repo.delete(cid, user["id"])


vehicle_cost_service = VehicleCostService()
