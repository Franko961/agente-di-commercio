from typing import Optional
from core.exceptions import NotFoundError
from core.utils import gen_id, now_iso
from repositories.expense_repository import expense_repository


class ExpenseService:
    def __init__(self, repo=expense_repository):
        self.repo = repo

    async def list_expenses(
        self,
        user: dict,
        category: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list:
        return await self.repo.find_many(user["id"], category, date_from, date_to)

    async def create_expense(self, user: dict, payload) -> dict:
        doc = {"id": gen_id(), "user_id": user["id"], **payload.model_dump(), "created_at": now_iso()}
        return await self.repo.insert(doc)

    async def update_expense(self, user: dict, eid: str, payload) -> None:
        existing = await self.repo.find_one(eid, user["id"])
        if not existing:
            raise NotFoundError("Spesa non trovata")
        await self.repo.update(eid, user["id"], payload.model_dump())

    async def delete_expense(self, user: dict, eid: str) -> None:
        await self.repo.delete(eid, user["id"])


expense_service = ExpenseService()
