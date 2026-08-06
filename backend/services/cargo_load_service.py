from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError, ValidationAppError
from repositories.cargo_load_repository import cargo_load_repository
from repositories.vehicle_repository import vehicle_repository
from repositories.client_repository import client_repository
from repositories.order_repository import order_repository


class CargoLoadService:
    def __init__(
        self, repo=cargo_load_repository, vehicles=vehicle_repository,
        clients=client_repository, orders=order_repository,
    ):
        self.repo = repo
        self.vehicles = vehicles
        self.clients = clients
        self.orders = orders

    async def list_loads(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def _validate_optional_links(self, user_id: str, client_id, order_id) -> None:
        """client_id/order_id sono facoltativi (vedi CargoLoadIn): se
        forniti però devono comunque appartenere all'utente, altrimenti un
        id di un altro account verrebbe accettato senza controllo."""
        if client_id and not await self.clients.find_one(client_id, user_id):
            raise ValidationAppError("Cliente non valido")
        if order_id and not await self.orders.find_one(order_id, user_id):
            raise ValidationAppError("Ordine non valido")

    async def create_load(self, user: dict, payload) -> dict:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        await self._validate_optional_links(user["id"], payload.client_id, payload.order_id)
        doc = {
            "id": gen_id(),
            "user_id": user["id"],
            "vehicle_id": payload.vehicle_id,
            "vehicle_plate": vehicle["plate"],
            "date": payload.date.isoformat(),
            "description": payload.description.strip(),
            "destination": (payload.destination or "").strip(),
            "notes": (payload.notes or "").strip(),
            "client_id": payload.client_id,
            "order_id": payload.order_id,
            "quantity": payload.quantity,
            "colli": payload.colli,
            "peso": payload.peso,
            "status": payload.status,
            "signature": None,
            "signer_name": None,
            "signed_at": None,
            "created_at": now_iso(),
        }
        return await self.repo.insert(doc)

    async def update_load(self, user: dict, lid: str, payload) -> None:
        vehicle = await self.vehicles.find_one(payload.vehicle_id, user["id"])
        if not vehicle:
            raise ValidationAppError("Mezzo non valido")
        await self._validate_optional_links(user["id"], payload.client_id, payload.order_id)
        ok = await self.repo.update(lid, user["id"], {
            "vehicle_id": payload.vehicle_id,
            "vehicle_plate": vehicle["plate"],
            "date": payload.date.isoformat(),
            "description": payload.description.strip(),
            "destination": (payload.destination or "").strip(),
            "notes": (payload.notes or "").strip(),
            "client_id": payload.client_id,
            "order_id": payload.order_id,
            "quantity": payload.quantity,
            "colli": payload.colli,
            "peso": payload.peso,
            "status": payload.status,
        })
        if not ok:
            raise NotFoundError("Carico non trovato")

    async def sign_load(self, user: dict, lid: str, signature: str, signer_name: str) -> None:
        """Firma di conferma consegna: come offer_service.sign_offer, porta
        anche lo stato a 'consegnato' (vedi cargo_load_repository.sign)."""
        matched = await self.repo.sign(lid, user["id"], signature, signer_name.strip(), now_iso())
        if not matched:
            raise NotFoundError("Carico non trovato")

    async def delete_load(self, user: dict, lid: str) -> None:
        await self.repo.delete(lid, user["id"])


cargo_load_service = CargoLoadService()
