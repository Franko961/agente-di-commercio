from core.exceptions import ConflictError, NotFoundError
from core.utils import gen_id, now_iso, now_local
from repositories.client_repository import client_repository
from repositories.mandante_repository import mandante_repository
from repositories.order_repository import order_repository
from services.commission_service import (
    calc_offer_total,
    commission_service,
    get_commission_rate,
)

# Stati che comportano la rimozione della provvigione collegata: un ordine
# annullato o reso non rappresenta più fatturato reale, quindi non deve più
# contare né come provvigione maturata né ai fini della scala premi.
_CANCELLED_STATUSES = ("annullato", "reso")

# Quante volte ritentare con il numero ordine successivo se quello generato
# automaticamente da next_order_number() collide con un numero già esistente
# (indice univoco su user_id+numero_ordine — vedi startup_service). Può
# succedere solo se un numero è stato in precedenza inserito a mano con un
# valore che il contatore automatico raggiunge più avanti (es. l'utente
# digita "ORD-0050" quando il contatore è ancora a 10): un caso raro ma
# reale, che altrimenti farebbe fallire la creazione dell'ordine con un
# errore che l'utente non saprebbe come risolvere.
_MAX_AUTO_NUMBER_RETRIES = 5


class OrderService:
    def __init__(
        self,
        repo=order_repository,
        mandante_repo=mandante_repository,
        client_repo=client_repository,
    ):
        self.repo = repo
        self.mandante_repo = mandante_repo
        self.client_repo = client_repo

    async def _validate_ownership(
        self, user_id: str, client_id: str, mandante_id: str
    ) -> None:
        """client_id/mandante_id arrivano dal payload dell'utente: senza
        verificarne l'appartenenza, un id di un altro utente (indovinato o
        enumerato) verrebbe comunque accettato — nessuna lettura successiva
        ne sarebbe compromessa (tutto resta filtrato per user_id), ma
        l'ordine referenzierebbe silenziosamente un cliente/mandante che non
        è il suo (es. la provvigione calcolata ricadrebbe sull'aliquota di
        default invece di dare un errore chiaro)."""
        if not await self.client_repo.find_one(client_id, user_id):
            raise NotFoundError("Cliente non trovato")
        if not await self.mandante_repo.find_one(mandante_id, user_id):
            raise NotFoundError("Mandante non trovato")

    async def _attach_commissions(self, user_id: str, orders: list) -> list:
        """Arricchisce ogni ordine con la provvigione collegata (se presente),
        per evitare che il frontend debba fare una chiamata separata per
        ordine. Recupera tutte le provvigioni dell'utente una sola volta e
        costruisce una mappa order_id -> commissione, invece di interrogare
        il DB una volta per ordine (che sarebbe O(ordini) round-trip)."""
        if not orders:
            return orders
        all_commissions = await commission_service.repo.find_many(user_id)
        by_order_id = {c["order_id"]: c for c in all_commissions if c.get("order_id")}
        for o in orders:
            o["commission"] = by_order_id.get(o["id"])
        return orders

    async def list_orders(self, user: dict, mandante_id: str = None) -> list:
        orders = await self.repo.find_many(user["id"], mandante_id)
        return await self._attach_commissions(user["id"], orders)

    async def list_orders_by_client(self, user: dict, client_id: str) -> list:
        orders = await self.repo.find_by_client(user["id"], client_id)
        return await self._attach_commissions(user["id"], orders)

    async def get_order(self, user: dict, oid: str) -> dict:
        order = await self.repo.find_one(oid, user["id"])
        if not order:
            raise NotFoundError("Ordine non trovato")
        commissions = await commission_service.repo.find_by_order(oid, user["id"])
        order["commission"] = commissions[0] if commissions else None
        return order

    async def _create_commission_for_order(self, user: dict, order_doc: dict) -> None:
        # A differenza delle offerte (bozza → inviata → accettata), un ordine è già
        # un fatto compiuto: la provvigione viene generata subito alla creazione,
        # con la stessa logica usata per un'offerta che passa ad "accettata".
        mandante = await self.mandante_repo.find_one(
            order_doc["mandante_id"], user["id"]
        )
        sale_type = order_doc.get("sale_type", "nuovo")
        rate = get_commission_rate(mandante, sale_type) if mandante else 5.0
        amount = order_doc.get("total", 0) * rate / 100
        comm = {
            "id": gen_id(),
            "user_id": user["id"],
            "offer_id": None,
            "order_id": order_doc["id"],
            "client_id": order_doc["client_id"],
            "mandante_id": order_doc["mandante_id"],
            "amount": round(amount, 2),
            "rate": rate,
            "base_amount": order_doc.get("total", 0),
            "sale_type": sale_type,
            "status": "maturato",
            # Vedi commission_service.check_and_award_bonus per il perché
            # "period" va calcolato in ora italiana e non UTC.
            "period": now_local().strftime("%Y-%m"),
            "created_at": now_iso(),
        }
        await commission_service.repo.insert(comm)
        await commission_service.check_and_award_bonus(
            user["id"], order_doc["mandante_id"]
        )

    async def _remove_commission_for_order(self, user_id: str, order: dict) -> None:
        """Rimuove la provvigione collegata a un ordine e ricalcola i bonus
        del mandante — usata sia alla cancellazione dell'ordine sia quando
        viene marcato annullato/reso senza cancellarlo."""
        await commission_service.repo.delete_by_order(order["id"], user_id)
        await commission_service.check_and_award_bonus(user_id, order["mandante_id"])

    async def _create_order_doc(
        self,
        user: dict,
        client_id: str,
        mandante_id: str,
        items: list,
        sale_type: str = "nuovo",
        notes: str = "",
        source_offer_id: str = None,
        numero_ordine: str = None,
        status: str = "confermato",
        payment_status: str = "non_pagato",
        expected_delivery_date: str = None,
        delivery_date: str = None,
    ) -> dict:
        total = calc_offer_total(items)
        auto_generate = not numero_ordine

        attempts = 0
        while True:
            if auto_generate:
                numero_ordine = await self.repo.next_order_number(user["id"])
            doc = {
                "id": gen_id(),
                "user_id": user["id"],
                "client_id": client_id,
                "mandante_id": mandante_id,
                "items": items,
                "sale_type": sale_type,
                "notes": notes,
                "total": total,
                "numero_ordine": numero_ordine,
                "status": status,
                "payment_status": payment_status,
                "expected_delivery_date": expected_delivery_date,
                "delivery_date": delivery_date,
                "source_offer_id": source_offer_id,
                "created_at": now_iso(),
            }
            try:
                await self.repo.insert(doc)
                break
            except ConflictError:
                if not auto_generate:
                    # Numero scelto a mano dall'utente: l'errore va restituito
                    # così com'è, è lui a dover scegliere un numero diverso.
                    raise
                attempts += 1
                if attempts >= _MAX_AUTO_NUMBER_RETRIES:
                    raise
                # Altrimenti ritenta con il numero automatico successivo
                # (vedi commento su _MAX_AUTO_NUMBER_RETRIES).

        if status not in _CANCELLED_STATUSES:
            await self._create_commission_for_order(user, doc)
        return doc

    async def create_order(self, user: dict, payload) -> dict:
        data = payload.model_dump()
        await self._validate_ownership(
            user["id"], data["client_id"], data["mandante_id"]
        )
        return await self._create_order_doc(
            user,
            data["client_id"],
            data["mandante_id"],
            data["items"],
            data.get("sale_type", "nuovo"),
            data.get("notes", ""),
            numero_ordine=data.get("numero_ordine"),
            status=data.get("status", "confermato"),
            payment_status=data.get("payment_status", "non_pagato"),
            expected_delivery_date=data.get("expected_delivery_date"),
            delivery_date=data.get("delivery_date"),
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
        try:
            return await self._create_order_doc(
                user,
                offer["client_id"],
                offer["mandante_id"],
                offer.get("items", []),
                offer.get("sale_type", "nuovo"),
                offer.get("notes", ""),
                source_offer_id=offer["id"],
            )
        except ConflictError:
            # Rete di sicurezza per la race condition che il check sopra da
            # solo non copre (due richieste concorrenti sulla stessa offerta
            # arrivate quasi insieme): l'indice univoco DB su
            # (user_id, source_offer_id) — vedi startup_service — ha bloccato
            # l'insert duplicato. Non è un vero errore per l'utente: l'altra
            # richiesta ha già creato l'ordine, lo recuperiamo e restituiamo
            # invece di propagare un 409, per restare idempotente anche qui.
            existing = await self.repo.find_by_source_offer(offer["id"], user["id"])
            if existing:
                return existing
            raise

    async def update_order(self, user: dict, oid: str, payload) -> None:
        """Modifica completa di un ordine esistente (righe, prezzi, mandante,
        tipo vendita, ecc. — non solo lo stato, per quello vedi
        update_order_status). Dato che la provvigione dipende da totale,
        mandante e tipo vendita, va ricalcolata da zero dopo ogni modifica:
        non basta aggiornarne l'importo, perché anche l'aliquota o il
        mandante beneficiario potrebbero essere cambiati."""
        existing = await self.repo.find_one(oid, user["id"])
        if not existing:
            raise NotFoundError("Ordine non trovato")

        # Catturati subito dopo il fetch, PRIMA di chiamare update(): non va
        # dato per scontato che self.repo.update() lasci intatto l'oggetto
        # `existing` già in mano (con MongoDB reale è così, ma il codice non
        # deve dipendere da quel dettaglio implementativo).
        old_mandante_id = existing["mandante_id"]

        data = payload.model_dump()
        await self._validate_ownership(
            user["id"], data["client_id"], data["mandante_id"]
        )
        data["total"] = calc_offer_total(data["items"])
        if not data.get("numero_ordine"):
            data["numero_ordine"] = existing.get(
                "numero_ordine"
            ) or await self.repo.next_order_number(user["id"])
        await self.repo.update(oid, user["id"], data)

        new_mandante_id = data["mandante_id"]
        is_cancelled = data.get("status") in _CANCELLED_STATUSES

        # Rigenera sempre la provvigione (a meno che l'ordine risulti
        # annullato/reso): più semplice e meno rischioso di provare ad
        # aggiornare in-place importo/aliquota/mandante della provvigione
        # esistente, e riusa la stessa logica già testata di creazione.
        await commission_service.repo.delete_by_order(oid, user["id"])
        updated_doc = {**existing, **data, "id": oid}
        if not is_cancelled:
            await self._create_commission_for_order(user, updated_doc)
        await commission_service.check_and_award_bonus(user["id"], old_mandante_id)
        if new_mandante_id != old_mandante_id:
            await commission_service.check_and_award_bonus(user["id"], new_mandante_id)

    async def update_order_status(self, user: dict, oid: str, payload) -> None:
        """Aggiornamento mirato di stato/evasione/pagamento/date, senza
        toccare righe e prezzi. Se lo stato passa a/da annullato o reso, la
        provvigione collegata viene rispettivamente rimossa o rigenerata."""
        order = await self.repo.find_one(oid, user["id"])
        if not order:
            raise NotFoundError("Ordine non trovato")
        old_status = order.get("status", "confermato")

        data = payload.model_dump(exclude_unset=True)
        if not data:
            return
        await self.repo.update_fields(oid, user["id"], data)

        new_status = data.get("status")
        if new_status is None:
            return
        was_cancelled = old_status in _CANCELLED_STATUSES
        is_cancelled = new_status in _CANCELLED_STATUSES

        if is_cancelled and not was_cancelled:
            await self._remove_commission_for_order(user["id"], order)
        elif was_cancelled and not is_cancelled:
            # Torna da annullato/reso a uno stato attivo: se non ha già una
            # provvigione (non dovrebbe averla, ma per sicurezza controlliamo),
            # la rigenera.
            existing_comm = await commission_service.repo.find_by_order(oid, user["id"])
            if not existing_comm:
                await self._create_commission_for_order(user, {**order, **data})

    async def delete_order(self, user: dict, oid: str) -> None:
        # A differenza delle offerte, per gli ordini la provvigione è legata a un
        # fatto già compiuto senza fase di conferma: cancellare l'ordine deve
        # quindi cancellare anche la provvigione generata, e ricalcolare eventuali
        # bonus del mandante che potrebbero non essere più raggiunti.
        order = await self.repo.find_one(oid, user["id"])
        await self.repo.delete(oid, user["id"])
        if order:
            await commission_service.repo.delete_by_order(oid, user["id"])
            await commission_service.check_and_award_bonus(
                user["id"], order["mandante_id"]
            )


order_service = OrderService()
