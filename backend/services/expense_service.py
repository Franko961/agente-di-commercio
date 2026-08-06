from typing import Optional
from core.exceptions import NotFoundError, ValidationAppError
from core.utils import gen_id, now_iso
from repositories.expense_repository import expense_repository

_READONLY_MESSAGES = {
    "flotta": (
        'Questa spesa è generata automaticamente da un costo Flotta: '
        'modificala o eliminala dalla sezione Flotta > Costi.'
    ),
    "personale": (
        'Questa spesa è generata automaticamente da un compenso dipendente: '
        'modificala o eliminala dalla scheda del dipendente > Compensi.'
    ),
}


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
        # Non solo un vincolo lato UI (vedi Spese.jsx): un utente potrebbe
        # chiamare direttamente PUT/DELETE su questa API, aggirando il
        # pulsante disabilitato e disallineando la spesa dal costo Flotta
        # che l'ha generata (vedi vehicle_cost_service.update_cost/
        # delete_cost, che sono l'unico percorso valido per modificarla).
        if existing.get("source") in _READONLY_MESSAGES:
            raise ValidationAppError(_READONLY_MESSAGES[existing["source"]])
        await self.repo.update(eid, user["id"], payload.model_dump())

    async def delete_expense(self, user: dict, eid: str) -> None:
        existing = await self.repo.find_one(eid, user["id"])
        if existing and existing.get("source") in _READONLY_MESSAGES:
            raise ValidationAppError(_READONLY_MESSAGES[existing["source"]])
        await self.repo.delete(eid, user["id"])


expense_service = ExpenseService()
