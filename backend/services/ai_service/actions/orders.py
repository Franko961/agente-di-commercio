from core.exceptions import NotFoundError
from models.order import ORDER_STATUSES, PAYMENT_STATUSES, OrderIn
from services.ai_service.actions._shared import resolve_line_items
from services.ai_service.catalog import _safe_float
from services.commission_service import calc_offer_total, get_commission_rate
from services.order_service import order_service


async def prepare_add_order(
    client_repo, mandante_repo, product_repo, tool_input: dict, user_id: str
) -> dict:
    """Risolve nomi cliente/mandante/prodotti e calcola il totale, SENZA
    scrivere nulla sul DB. Usato per mostrare la scheda di conferma prima
    di registrare un ordine (a differenza di un'offerta, un ordine è già
    un fatto compiuto: niente stato bozza/accettata)."""
    client_name = tool_input.get("client_name", "")
    mandante_name = tool_input.get("mandante_name", "")

    cli = await client_repo.find_by_name_regex(user_id, client_name)
    if not cli:
        return {"error": f"Cliente '{client_name}' non trovato nel CRM."}

    mand = await mandante_repo.find_by_name_regex(user_id, mandante_name)
    if not mand:
        return {"error": f"Mandante '{mandante_name}' non trovato nel CRM."}

    items = await resolve_line_items(
        product_repo, tool_input, user_id, mand["id"], f"Ordine {cli['company_name']}"
    )

    total = calc_offer_total(items)
    if total <= 0:
        return {
            "error": "L'importo dell'ordine deve essere maggiore di zero. Specifica un importo o dei prezzi validi."
        }

    sale_type = tool_input.get("sale_type", "nuovo")
    if sale_type not in ("nuovo", "rinnovo"):
        sale_type = "nuovo"
    status = tool_input.get("status") or "confermato"
    if status not in ORDER_STATUSES:
        status = "confermato"
    payment_status = tool_input.get("payment_status") or "non_pagato"
    if payment_status not in PAYMENT_STATUSES:
        payment_status = "non_pagato"
    notes = tool_input.get("notes", "")

    return {
        "tool_name": "add_order",
        "summary": {
            "client_name": cli["company_name"],
            "mandante_name": mand["name"],
            "amount": total,
            "sale_type": sale_type,
            "status": status,
            "payment_status": payment_status,
        },
        "resolved_input": {
            "client_id": cli["id"],
            "client_name": cli["company_name"],
            "mandante_id": mand["id"],
            "mandante_name": mand["name"],
            "items": items,
            "amount": total,
            "sale_type": sale_type,
            "status": status,
            "payment_status": payment_status,
            "notes": notes,
        },
    }


async def finalize_add_order(mandante_repo, user_id: str, resolved: dict) -> str:
    """Scrive davvero l'ordine sul DB, a partire da un resolved_input già
    risolto da prepare_add_order (eventualmente modificato dall'utente
    nella scheda di conferma). Il payload può arrivare anche direttamente
    da /api/ai/execute-action, quindi va ri-validato qui: non ci si può
    fidare che sia sempre passato prima da prepare_add_order."""
    items = resolved.get("items") or []
    items = [
        {
            "product_id": it.get("product_id"),
            "description": it.get("description", "Ordine"),
            "quantity": max(_safe_float(it.get("quantity"), 1), 0.01),
            "unit_price": max(_safe_float(it.get("unit_price"), 0), 0),
            "discount": max(_safe_float(it.get("discount"), 0), 0),
        }
        for it in items
    ]
    amount = resolved.get("amount")
    client_name = resolved.get("client_name", "")
    if amount is not None and amount != "":
        amount_f = _safe_float(amount, None)
        if amount_f is not None and (
            not items or round(calc_offer_total(items), 2) != round(amount_f, 2)
        ):
            items = [
                {
                    "product_id": None,
                    "description": f"Ordine {client_name}",
                    "quantity": 1,
                    "unit_price": amount_f,
                    "discount": 0,
                }
            ]

    total = calc_offer_total(items)
    if total <= 0:
        return "❌ L'importo deve essere maggiore di zero: ordine non registrato."

    sale_type = resolved.get("sale_type", "nuovo")
    if sale_type not in ("nuovo", "rinnovo"):
        sale_type = "nuovo"
    status = resolved.get("status") or "confermato"
    if status not in ORDER_STATUSES:
        status = "confermato"
    payment_status = resolved.get("payment_status") or "non_pagato"
    if payment_status not in PAYMENT_STATUSES:
        payment_status = "non_pagato"

    mand = await mandante_repo.find_one(resolved["mandante_id"], user_id)
    if not mand:
        return "❌ Mandante non più trovato nel CRM."

    try:
        order_in = OrderIn(
            client_id=resolved["client_id"],
            mandante_id=resolved["mandante_id"],
            items=items,
            sale_type=sale_type,
            notes=resolved.get("notes", ""),
            status=status,
            payment_status=payment_status,
        )
        order = await order_service.create_order({"id": user_id}, order_in)
    except NotFoundError:
        return "❌ Cliente o mandante non più trovati nel CRM."

    msg = f"✅ Ordine {order.get('numero_ordine', '')} registrato: {client_name} - {mand['name']} - €{total:.2f} ({sale_type}), stato: {status}."
    if status not in ("annullato", "reso"):
        rate = get_commission_rate(mand, sale_type)
        comm_amount = round(total * rate / 100, 2)
        msg += f" Provvigione generata: €{comm_amount:.2f} ({rate}%)."
    return msg
