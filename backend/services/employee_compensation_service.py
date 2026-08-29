from core.exceptions import NotFoundError, ValidationAppError
from core.utils import gen_id, now_iso
from repositories.employee_compensation_repository import (
    employee_compensation_repository,
)
from repositories.employee_repository import employee_repository
from repositories.expense_repository import expense_repository

# Le categorie di Spese (models/expense.py EXPENSE_CATEGORIES) sono pensate
# per le spese personali dell'agente, non per il costo del personale: nessuna
# coincide davvero, quindi ogni compenso confluisce in "altro" — stesso
# principio già applicato ai costi Flotta non-carburante (vedi
# vehicle_cost_service.py), il dettaglio resta leggibile nella descrizione.
_COMPENSATION_TYPE_LABELS = {
    "stipendio": "Stipendio",
    "bonus": "Bonus",
    "rimborso": "Rimborso",
    "altro": "Altro",
}


def _expense_description(employee_name: str, comp_type: str, notes: str) -> str:
    label = _COMPENSATION_TYPE_LABELS.get(comp_type, comp_type)
    base = f"Personale {employee_name} — {label}"
    return f"{base}: {notes}" if notes else base


class EmployeeCompensationService:
    def __init__(
        self,
        repo=employee_compensation_repository,
        employees=employee_repository,
        expenses=expense_repository,
    ):
        self.repo = repo
        self.employees = employees
        self.expenses = expenses

    async def _validate_employee(self, user_id: str, employee_id: str) -> dict:
        employee = await self.employees.find_one(employee_id, user_id)
        if not employee:
            raise ValidationAppError("Dipendente non valido")
        return employee

    async def list_compensations(self, user: dict, employee_id: str) -> list:
        await self._validate_employee(user["id"], employee_id)
        return await self.repo.find_many(employee_id, user["id"])

    async def create_compensation(self, user: dict, employee_id: str, payload) -> dict:
        """Ogni compenso genera automaticamente una voce Spese collegata
        (expense_id), come già fatto per i costi Flotta (vedi
        vehicle_cost_service.create_cost): la spesa generata è di sola
        lettura da Spese.jsx (expense_service blocca update/delete se
        source == "personale") — va modificata/eliminata da qui, che
        propaga su entrambi i lati."""
        employee = await self._validate_employee(user["id"], employee_id)
        comp_id = gen_id()
        notes = (payload.notes or "").strip()
        date_iso = payload.date.isoformat()
        employee_name = f"{employee['name']} {employee.get('surname', '')}".strip()

        expense_doc = {
            "id": gen_id(),
            "user_id": user["id"],
            "date": date_iso,
            "category": "altro",
            "description": _expense_description(employee_name, payload.type, notes),
            "amount": payload.amount,
            "client_id": None,
            "notes": "",
            "receipt_document_id": None,
            "source": "personale",
            "employee_compensation_id": comp_id,
            "created_at": now_iso(),
        }
        await self.expenses.insert(expense_doc)

        doc = {
            "id": comp_id,
            "user_id": user["id"],
            "employee_id": employee_id,
            "type": payload.type,
            "amount": payload.amount,
            "date": date_iso,
            "notes": notes,
            "expense_id": expense_doc["id"],
            "created_at": now_iso(),
        }
        try:
            return await self.repo.insert(doc)
        except Exception:
            # Rollback esplicito: senza transazione Mongo, un fallimento qui
            # lascerebbe la spesa già inserita sopra orfana (nessun compenso
            # a puntarla) per sempre — non essendoci ancora nulla che la
            # referenzi da questo lato, cancellarla è sempre sicuro (non
            # esiste per definizione la corsa in cui qualcun altro l'ha già
            # letta/collegata nel frattempo).
            await self.expenses.delete(expense_doc["id"], user["id"])
            raise

    async def update_compensation(
        self, user: dict, employee_id: str, cid: str, payload
    ) -> None:
        existing = await self.repo.find_one(cid, user["id"], employee_id)
        if not existing:
            raise NotFoundError("Compenso non trovato")
        employee = await self._validate_employee(user["id"], employee_id)

        notes = (payload.notes or "").strip()
        date_iso = payload.date.isoformat()
        employee_name = f"{employee['name']} {employee.get('surname', '')}".strip()

        await self.repo.update(
            cid,
            user["id"],
            employee_id,
            {
                "type": payload.type,
                "amount": payload.amount,
                "date": date_iso,
                "notes": notes,
            },
        )

        if existing.get("expense_id"):
            await self.expenses.update(
                existing["expense_id"],
                user["id"],
                {
                    "date": date_iso,
                    "description": _expense_description(
                        employee_name, payload.type, notes
                    ),
                    "amount": payload.amount,
                },
            )

    async def delete_compensation(self, user: dict, employee_id: str, cid: str) -> None:
        existing = await self.repo.find_one(cid, user["id"], employee_id)
        if existing and existing.get("expense_id"):
            await self.expenses.delete(existing["expense_id"], user["id"])
        await self.repo.delete(cid, user["id"], employee_id)


employee_compensation_service = EmployeeCompensationService()
