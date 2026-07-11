from core.utils import gen_id, now_iso
from repositories.lead_repository import lead_repository

class LeadService:
    def __init__(self, repo=lead_repository):
        self.repo = repo

    async def list_leads(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_lead(self, user: dict, payload) -> dict:
        doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
        return await self.repo.insert(doc)

    async def update_lead(self, user: dict, lid: str, payload) -> None:
        await self.repo.update(lid, user["id"], payload.model_dump())

    async def update_status(self, user: dict, lid: str, status: str) -> None:
        await self.repo.update_status(lid, user["id"], status)

    async def delete_lead(self, user: dict, lid: str) -> None:
        await self.repo.delete(lid, user["id"])


lead_service = LeadService()
