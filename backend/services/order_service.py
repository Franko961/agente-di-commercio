from core.utils import gen_id, now_iso, now_local
from repositories.order_repository import order_repository
from repositories.mandante_repository import mandante_repository
from services.commission_service import calc_offer_total, get_commission_rate, commission_service


class OrderService:
    def __init__(self, repo=order_repository, mandante_repo=mandante_repository):
        self.repo = repo
        self.mandante_repo = mandante_repo

    async def list_orders(self, user: dict, mandante_id: str = None) -> list:
        return await self.repo.find_many(user["id"], mandante_id)

    async def list_orders_by_client(self, user: dict, client_id: str) -> list:
        return await self.repo.find_by_client(user["id"], client_id)

    async def _create_commission_for_order(self, user: dict, order_doc: dict) -> None:
        # A differenza delle offerte (bozza → inviata → accettata), un ordine è già
        # un fatto compiuto: la provvigione viene generata subito alla creazione,
        # con la stessa logica usata per un'offerta che passa ad "accettata".
        mandante = await self.mandante_repo.find_one(order_doc["mandante_id"], user["id"])
        sale_type = order_doc.get("sale_type", "nuovo")
        rate = get_commission_rate(mandante, sale_type) if mandante else 5.0
        amount = order_doc.get("total", 0) * rate / 100
        comm = {
            "id": gen_id(), "user_id": user["id"], "offer_id": None, "order_id": order_doc["id"],
            "client_id": order_doc["client_id"], "mandante_id": order_doc["mandante_id"],
            "amount": round(amount, 2), "rate": rate, "base_amount": order_doc.get("total", 0),
            "sale_type": sale_type, "status": "maturato",
            # Vedi commission_service.check_and_award_bonus per il perché
            # "period" va calcolato in ora italiana e non UTC.
            "period": now_local().strftime("%Y-%m"),
            "created_at": now_iso(),
        }
        await commission_service.repo.insert(comm)
        await commission_service.check_and_award_bonus(user["id"], order_doc["mandante_id"])

    async def _create_order_doc(self, user: dict, client_id: str, mandante_id: str, items: list,
                                 sale_type: str = "nuovo", notes: str = "", source_offer_id: str = None) -> dict:
        total = calc_offer_total(items)
        doc = {
            "id": gen_id(), "user_id": user["id"], "client_id": client_id, "mandante_id": mandante_id,
            "items": items, "sale_type": sale_type, "notes": notes, "total": total,
            "source_offer_id": source_offer_id, "created_at": now_iso(),
        }
        await self.repo.insert(doc)
        await self._create_commission_for_order(user, doc)
        return doc

    async def create_order(self, user: dict, payload) -> dict:
        data = payload.model_dump()
        return await self._create_order_doc(
            user, data["client_id"], data["mandante_id"], data["items"],
            data.get("sale_type", "nuovo"), data.get("notes", ""),
        )

    async def create_from_offer(self, user: dict, offer: dict) -> dict:
        """Trasforma un'offerta accettata/firmata nel suo ordine corrispondente
        (che a sua volta genera la provvigione). Idempotente: se per questa
        offerta esiste già un ordine, lo restituisce senza duplicarlo — utile
        perché un'offerta può passare ad "accettata" sia dal pulsante di stato
        sia dalla firma digitale, e i due percorsi non devono generare due ordini."""
        existing = await self.repo.find_by_source_offer(offer["id"], user["id"])
        if existing:
            return existing
        return await self._create_order_doc(
            user, offer["client_id"], offer["mandante_id"], offer.get("items", []),
            offer.get("sale_type", "nuovo"), offer.get("notes", ""),
            source_offer_id=offer["id"],
        )

    async def delete_order(self, user: dict, oid: str) -> None:
        # A differenza delle offerte, per gli ordini la provvigione è legata a un
        # fatto già compiuto senza fase di conferma: cancellare l'ordine deve
        # quindi cancellare anche la provvigione generata, e ricalcolare eventuali
        # bonus del mandante che potrebbero non essere più raggiunti.
        order = await self.repo.find_one(oid, user["id"])
        await self.repo.delete(oid, user["id"])
        if order:
            await commission_service.repo.delete_by_order(oid, user["id"])
            await commission_service.check_and_award_bonus(user["id"], order["mandante_id"])


order_service = OrderService()
