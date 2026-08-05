import secrets

from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError
from repositories.employee_repository import employee_repository


class EmployeeService:
    def __init__(self, repo=employee_repository):
        self.repo = repo

    async def list_employees(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_employee(self, user: dict, payload) -> dict:
        doc = {
            "id": gen_id(), "user_id": user["id"],
            **payload.model_dump(),
            # Non serve un hash come per il reset password: qui il token è
            # pensato per essere riusato più volte dallo stesso dipendente
            # (link personale salvato), non consumato una volta sola — un
            # eventuale abuso (indovinare il token di un collega) espone al
            # più il nome del dipendente e la possibilità di inviare una
            # richiesta a suo nome, non un dato sensibile come una password.
            "request_token": secrets.token_urlsafe(24),
            "active": True,
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_employee(self, user: dict, eid: str, payload) -> None:
        ok = await self.repo.update(eid, user["id"], payload.model_dump())
        if not ok:
            raise NotFoundError("Dipendente non trovato")

    async def delete_employee(self, user: dict, eid: str) -> None:
        await self.repo.delete(eid, user["id"])

    async def get_by_token(self, token: str) -> dict:
        employee = await self.repo.find_by_token(token)
        if not employee or not employee.get("active", True):
            raise NotFoundError("Link non valido")
        return employee


employee_service = EmployeeService()
