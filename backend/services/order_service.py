from datetime import datetime, timezone
from core.utils import gen_id, now_iso
from repositories.order_repository import order_repository
from repositories.mandante_repository import mandante_repository
from services.commission_service import calc_offer_total, get_commission_rate, commission_service


class OrderService:
    def __init__(self, repo=order_repository, mandante_repo=mandante_repository):
        self.repo = repo
        self.mandante_repo = mandante_repo

    async def list_orders(self, user: dict) -> list:
        return await self.repo.find_many(user["id"])

    async def list_orders_by_client(self, user: dict, client_id: str) -> list:
        return await self.repo.find_by_client(user["id"], client_id)

    async def create_order(self, user: dict, payload) -> dict:
        data = payload.model_dump()
        data["total"] = calc_offer_total(data["items"])
        doc = {"id": gen_id(), "user_id": user["id"], **data, "created_at": now_iso()}
        await self.repo.insert(doc)

        # A differenza delle offerte (bozza → inviata → accettata), un ordine è già
        # un fatto compiuto: la provvigione viene generata subito alla creazione,
        # con la stessa logica usata per un'offerta che passa ad "accettata".
        mandante = await self.mandante_repo.find_one(doc["mandante_id"], user["id"])
        sale_type = doc.get("sale_type", "nuovo")
        rate = get_commission_rate(mandante, sale_type) if mandante else 5.0
        amount = doc.get("total", 0) * rate / 100
        comm = {
            "id": gen_id(), "user_id": user["id"], "offer_id": None, "order_id": doc["id"],
            "client_id": doc["client_id"], "mandante_id": doc["mandante_id"],
            "amount": round(amount, 2), "rate": rate, "base_amount": doc.get("total", 0),
            "sale_type": sale_type, "status": "maturato",
            "period": datetime.now(timezone.utc).strftime("%Y-%m"),
            "created_at": now_iso(),
        }
        await commission_service.repo.insert(comm)
        await commission_service.check_and_award_bonus(user["id"], doc["mandante_id"])
        return doc

    async def delete_order(self, user: dict, oid: str) -> None:
        # Nota: come per le offerte (delete_offer), cancellare un ordine non rimuove
        # automaticamente la provvigione già generata — comportamento coerente con
        # quello esistente per le offerte.
        await self.repo.delete(oid, user["id"])


order_service = OrderService()
