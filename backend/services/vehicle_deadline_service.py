from core.exceptions import NotFoundError, ValidationAppError
from core.utils import gen_id, now_iso, now_local
from repositories.vehicle_deadline_repository import vehicle_deadline_repository
from repositories.vehicle_repository import vehicle_repository


class VehicleDeadlineService:
    def __init__(self, repo=vehicle_deadline_repository, vehicles=vehicle_repository):
        self.repo = repo
        self.vehicles = vehicles

    async def list_deadlines(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_deadline(self, user: dict, payload) -> dict:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            "vehicle_id": payload.vehicle_id,
            # Denormalizzato apposta: se il mezzo viene poi eliminato, la
            # scadenza resta leggibile nello storico invece di mostrare un
            # riferimento orfano (stesso principio di employee_name in
            # leave_request_service.py).
            "vehicle_plate": vehicle["plate"],
            "type": payload.type,
            "due_date": payload.due_date.isoformat(),
            "note": (payload.note or "").strip(),
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_deadline(self, user: dict, did: str, payload) -> None:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        ok = await self.repo.update(
            did,
            user["id"],
            {
                "vehicle_id": payload.vehicle_id,
                "vehicle_plate": vehicle["plate"],
                "type": payload.type,
                "due_date": payload.due_date.isoformat(),
                "note": (payload.note or "").strip(),
            },
        )
        if not ok:
            raise NotFoundError("Scadenza non trovata")

    async def delete_deadline(self, user: dict, did: str) -> None:
        await self.repo.delete(did, user["id"])

    async def next_deadline(
        self, user: dict, vehicle_id: str, deadline_type: str = "revisione"
    ):
        """Prossima scadenza FUTURA (o odierna) di un dato tipo per il
        mezzo — usato dalla tab "Mezzo assegnato" della scheda dipendente
        al posto di un inesistente "ultimo controllo" (SalesFly traccia
        solo le prossime scadenze, non lo storico dei controlli già
        effettuati). Esclude le scadenze già passate: senza il filtro su
        due_date, una revisione mai aggiornata dopo essere scaduta
        risultava comunque "la prossima" solo perché la più vicina in
        ordine cronologico, anche se ormai nel passato."""
        today = now_local().strftime("%Y-%m-%d")
        deadlines = await self.repo.find_many(user["id"])
        candidates = sorted(
            (
                d
                for d in deadlines
                if d["vehicle_id"] == vehicle_id
                and d["type"] == deadline_type
                and d["due_date"] >= today
            ),
            key=lambda d: d["due_date"],
        )
        return candidates[0] if candidates else None


vehicle_deadline_service = VehicleDeadlineService()
