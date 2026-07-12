from datetime import datetime, timezone
from core.utils import gen_id, now_iso
from core.exceptions import NotFoundError
from repositories.offer_repository import offer_repository
from repositories.mandante_repository import mandante_repository
from services.commission_service import calc_offer_total, get_commission_rate, commission_service


class OfferService:
    def __init__(self, repo=offer_repository, mandante_repo=mandante_repository):
        self.repo = repo
        self.mandante_repo = mandante_repo

    async def list_offers(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def create_offer(self, user: dict, payload) -> dict:
        data = payload.model_dump()
        data["total"] = calc_offer_total(data["items"])
        doc = {"id": gen_id(), "user_id": user["id"], **data, "created_at": now_iso()}
        return await self.repo.insert(doc)

    async def update_offer(self, user: dict, oid: str, payload) -> None:
        data = payload.model_dump()
        data["total"] = calc_offer_total(data["items"])
        await self.repo.update(oid, user["id"], data)

    async def update_offer_status(self, user: dict, oid: str, new_status: str) -> None:
        offer = await self.repo.find_one(oid, user["id"])
        if not offer:
            raise NotFoundError("Offerta non trovata")
        await self.repo.update_status(oid, user["id"], new_status)
        # Se accettata, crea la commissione
        if new_status == "accettata" and offer.get("status") != "accettata":
            mandante = await self.mandante_repo.find_one(offer["mandante_id"], user["id"])
            sale_type = offer.get("sale_type", "nuovo")
            rate = get_commission_rate(mandante, sale_type) if mandante else 5.0
            amount = offer.get("total", 0) * rate / 100
            comm = {
                "id": gen_id(), "user_id": user["id"], "offer_id": oid,
                "client_id": offer["client_id"], "mandante_id": offer["mandante_id"],
                "amount": round(amount, 2), "rate": rate, "base_amount": offer.get("total", 0),
                "sale_type": sale_type, "status": "maturato",
                "period": datetime.now(timezone.utc).strftime("%Y-%m"),
                "created_at": now_iso(),
            }
            await commission_service.repo.insert(comm)
            await commission_service.check_and_award_bonus(user["id"], offer["mandante_id"])

    async def delete_offer(self, user: dict, oid: str) -> None:
        await self.repo.delete(oid, user["id"])

    async def sign_offer(self, user: dict, oid: str, signature: str, signer_name: str) -> None:
        signed_at = now_iso()
        matched = await self.repo.sign(oid, user["id"], signature, signer_name, signed_at)
        if not matched:
            raise NotFoundError("Offerta non trovata")

        # Auto-crea la commissione se non esiste già per questa offerta
        offer = await self.repo.find_one(oid, user["id"])
        existing = await commission_service.repo.find_by_offer(oid, user["id"])
        if not existing and offer:
            mandante = await self.mandante_repo.find_one(offer["mandante_id"], user["id"])
            sale_type = offer.get("sale_type", "nuovo")
            rate = get_commission_rate(mandante, sale_type) if mandante else 5.0
            amount = offer.get("total", 0) * rate / 100
            comm = {
                "id": gen_id(), "user_id": user["id"], "offer_id": oid,
                "client_id": offer["client_id"], "mandante_id": offer["mandante_id"],
                "amount": round(amount, 2), "rate": rate, "base_amount": offer.get("total", 0),
                "sale_type": sale_type, "status": "maturato",
                "period": datetime.now(timezone.utc).strftime("%Y-%m"),
                "created_at": now_iso(),
            }
            await commission_service.repo.insert(comm)
            await commission_service.check_and_award_bonus(user["id"], offer["mandante_id"])


offer_service = OfferService()
