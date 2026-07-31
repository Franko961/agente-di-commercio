from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError
from repositories.offer_repository import offer_repository
from repositories.mandante_repository import mandante_repository
from repositories.client_repository import client_repository
from services.commission_service import calc_offer_total
from services.order_service import order_service


class OfferService:
    def __init__(self, repo=offer_repository, mandante_repo=mandante_repository, client_repo=client_repository):
        self.repo = repo
        self.mandante_repo = mandante_repo
        self.client_repo = client_repo

    async def _validate_ownership(self, user_id: str, client_id: str, mandante_id: str) -> None:
        """Stessa ragione di OrderService._validate_ownership: client_id/
        mandante_id arrivano dal payload dell'utente e senza questa verifica
        un id di un altro utente verrebbe comunque accettato."""
        if not await self.client_repo.find_one(client_id, user_id):
            raise NotFoundError("Cliente non trovato")
        if not await self.mandante_repo.find_one(mandante_id, user_id):
            raise NotFoundError("Mandante non trovato")

    async def list_offers(self, user: dict, mandante_id: str = None) -> list:
        return await self.repo.find_many(user["id"], mandante_id)

    async def create_offer(self, user: dict, payload) -> dict:
        data = payload.model_dump()
        await self._validate_ownership(user["id"], data["client_id"], data["mandante_id"])
        data["total"] = calc_offer_total(data["items"])
        doc = {"id": gen_id(), "user_id": user["id"], **data, "created_at": now_iso()}
        return await self.repo.insert(doc)

    async def update_offer(self, user: dict, oid: str, payload) -> None:
        data = payload.model_dump()
        await self._validate_ownership(user["id"], data["client_id"], data["mandante_id"])
        data["total"] = calc_offer_total(data["items"])
        await self.repo.update(oid, user["id"], data)

    async def update_offer_status(self, user: dict, oid: str, new_status: str) -> None:
        offer = await self.repo.find_one(oid, user["id"])
        if not offer:
            raise NotFoundError("Offerta non trovata")
        await self.repo.update_status(oid, user["id"], new_status)
        # Un'offerta accettata si trasforma nel suo ordine corrispondente, che a
        # sua volta genera la provvigione (vedi order_service.create_from_offer).
        if new_status == "accettata" and offer.get("status") != "accettata":
            await order_service.create_from_offer(user, offer)

    async def delete_offer(self, user: dict, oid: str) -> None:
        await self.repo.delete(oid, user["id"])

    async def sign_offer(self, user: dict, oid: str, signature: str, signer_name: str) -> None:
        signed_at = now_iso()
        matched = await self.repo.sign(oid, user["id"], signature, signer_name, signed_at)
        if not matched:
            raise NotFoundError("Offerta non trovata")

        # La firma porta comunque lo stato a "accettata" (vedi offer_repository.sign):
        # anche qui l'offerta si trasforma nel suo ordine. create_from_offer è
        # idempotente, quindi firmare un'offerta già accettata da pulsante di stato
        # non genera un secondo ordine/provvigione.
        offer = await self.repo.find_one(oid, user["id"])
        if offer:
            await order_service.create_from_offer(user, offer)


offer_service = OfferService()
