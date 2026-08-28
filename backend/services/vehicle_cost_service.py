from core.exceptions import NotFoundError, ValidationAppError
from core.utils import gen_id, now_iso
from repositories.expense_repository import expense_repository
from repositories.vehicle_cost_repository import vehicle_cost_repository
from repositories.vehicle_repository import vehicle_repository

# La tassonomia categorie di Spese (vedi models/expense.py EXPENSE_CATEGORIES)
# è pensata per le spese personali dell'agente (vitto, alloggio, enasarco...),
# non per la flotta: solo "carburante" coincide davvero. Le altre categorie
# Flotta confluiscono in "altro" — il dettaglio (tipo di costo, targa) resta
# comunque leggibile nella descrizione della spesa generata.
_EXPENSE_CATEGORY_FOR_COST = {"carburante": "carburante"}


def _expense_category_for(cost_category: str) -> str:
    return _EXPENSE_CATEGORY_FOR_COST.get(cost_category, "altro")


def _expense_description(plate: str, description: str) -> str:
    return f"Flotta {plate}" + (f" — {description}" if description else "")


class VehicleCostService:
    def __init__(
        self,
        repo=vehicle_cost_repository,
        vehicles=vehicle_repository,
        expenses=expense_repository,
    ):
        self.repo = repo
        self.vehicles = vehicles
        self.expenses = expenses

    async def list_costs(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_cost(self, user: dict, payload) -> dict:
        """Ogni costo Flotta genera automaticamente una voce Spese
        collegata (expense_id), così dashboard/AI/report che già leggono
        da Spese vedono sempre dati coerenti senza dover conoscere
        l'esistenza del modulo Flotta. La spesa generata è di sola lettura
        da Spese.jsx (vedi expense_service: blocca update/delete se
        source == "flotta") — va modificata/eliminata da qui, che
        propaga la modifica su entrambi i lati (vedi update_cost/
        delete_cost)."""
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")

        cost_id = gen_id()
        description = (payload.description or "").strip()
        date_iso = payload.date.isoformat()

        expense_doc = {
            "id": gen_id(),
            "user_id": user["id"],
            "date": date_iso,
            "category": _expense_category_for(payload.category),
            "description": _expense_description(vehicle["plate"], description),
            "amount": payload.amount,
            "client_id": None,
            "notes": "",
            "receipt_document_id": None,
            "source": "flotta",
            "vehicle_cost_id": cost_id,
            "created_at": now_iso(),
        }
        await self.expenses.insert(expense_doc)

        doc = {
            "id": cost_id,
            "user_id": user["id"],
            "vehicle_id": payload.vehicle_id,
            "vehicle_plate": vehicle["plate"],
            "category": payload.category,
            "amount": payload.amount,
            "date": date_iso,
            "description": description,
            "expense_id": expense_doc["id"],
            "created_at": now_iso(),
        }
        try:
            return await self.repo.insert(doc)
        except Exception:
            # Rollback esplicito: vedi lo stesso commento in
            # employee_compensation_service.create_compensation — senza
            # transazione Mongo, un fallimento qui lascerebbe la spesa
            # appena inserita orfana per sempre.
            await self.expenses.delete(expense_doc["id"], user["id"])
            raise

    async def update_cost(self, user: dict, cid: str, payload) -> None:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        existing = await self.repo.find_one(cid, user["id"])
        if not existing:
            raise NotFoundError("Costo non trovato")

        description = (payload.description or "").strip()
        date_iso = payload.date.isoformat()

        await self.repo.update(
            cid,
            user["id"],
            {
                "vehicle_id": payload.vehicle_id,
                "vehicle_plate": vehicle["plate"],
                "category": payload.category,
                "amount": payload.amount,
                "date": date_iso,
                "description": description,
            },
        )

        if existing.get("expense_id"):
            await self.expenses.update(
                existing["expense_id"],
                user["id"],
                {
                    "date": date_iso,
                    "category": _expense_category_for(payload.category),
                    "description": _expense_description(vehicle["plate"], description),
                    "amount": payload.amount,
                },
            )

    async def delete_cost(self, user: dict, cid: str) -> None:
        existing = await self.repo.find_one(cid, user["id"])
        if existing and existing.get("expense_id"):
            await self.expenses.delete(existing["expense_id"], user["id"])
        await self.repo.delete(cid, user["id"])


vehicle_cost_service = VehicleCostService()
