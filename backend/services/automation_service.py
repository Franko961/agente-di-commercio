from core.utils import gen_id, now_iso
from repositories.automation_repository import automation_repository


class AutomationService:
    def __init__(self, repo=automation_repository):
        self.repo = repo

    async def list_automations(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_automation(self, user: dict, payload) -> dict:
        doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
        return await self.repo.insert(doc)

    async def update_automation(self, user: dict, aid: str, payload) -> None:
        await self.repo.update(aid, user["id"], payload.model_dump())

    async def delete_automation(self, user: dict, aid: str) -> None:
        await self.repo.delete(aid, user["id"])


automation_service = AutomationService()
