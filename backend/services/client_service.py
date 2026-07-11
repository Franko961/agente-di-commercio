import uuid
from datetime import datetime, timezone
from core.exceptions import NotFoundError
from core.database import db
from repositories.client_repository import client_repository

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ClientService:
    def __init__(self, repo=client_repository):
        self.repo = repo

    async def list_clients(self, user: dict, zone=None, sector=None, potential=None, q=None):
        filters = {}
        if zone: filters["zone"] = zone
        if sector: filters["sector"] = sector
        if potential: filters["potential"] = potential
        if q:
            filters["$or"] = [
                {"company_name": {"$regex": q, "$options": "i"}},
                {"contact_name": {"$regex": q, "$options": "i"}},
                {"city": {"$regex": q, "$options": "i"}},
            ]
        return await self.repo.find_many(user["id"], filters)

    async def create_client(self, user: dict, payload) -> dict:
        doc = {"id": str(uuid.uuid4()), "user_id": user["id"], **payload.model_dump(), "created_at": _now_iso()}
        return await self.repo.insert(doc)

    async def get_client(self, user: dict, cid: str) -> dict:
        c = await self.repo.find_one(cid, user["id"])
        if not c:
            raise NotFoundError("Cliente non trovato")
        offers = await db.offers.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
        appts = await db.appointments.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
        docs = await db.documents.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
        commissions = await db.commissions.find({"client_id": cid, "user_id": user["id"]}, {"_id": 0}).to_list(500)
        return {"client": c, "offers": offers, "appointments": appts, "documents": docs, "commissions": commissions}

    async def update_client(self, user: dict, cid: str, payload) -> None:
        ok = await self.repo.update(cid, user["id"], payload.model_dump())
        if not ok:
            raise NotFoundError("Cliente non trovato")

    async def delete_client(self, user: dict, cid: str) -> None:
        await self.repo.delete(cid, user["id"])


client_service = ClientService()
