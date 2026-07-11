from core.utils import gen_id, now_iso
from repositories.appointment_repository import appointment_repository

class AppointmentService:
    def __init__(self, repo=appointment_repository):
        self.repo = repo

    async def list_appointments(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_appointment(self, user: dict, payload) -> dict:
        doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
        return await self.repo.insert(doc)

    async def update_appointment(self, user: dict, aid: str, payload) -> None:
        await self.repo.update(aid, user["id"], payload.model_dump())

    async def delete_appointment(self, user: dict, aid: str) -> None:
        await self.repo.delete(aid, user["id"])


appointment_service = AppointmentService()
