from core.utils import gen_id, now_iso
from services.ai_service.catalog import _safe_float
from services.ai_service.actions._shared import resolve_line_items
from services.commission_service import calc_offer_total, get_commission_rate
from services.order_service import order_service


async def prepare_add_offer(client_repo, mandante_repo, product_repo, tool_input: dict, user_id: str) -> dict:
    """Risolve nomi cliente/mandante/prodotti e calcola il totale, SENZA
    scrivere nulla sul DB. Usato per mostrare la scheda di conferma prima
    di registrare una vendita/offerta."""
    client_name = tool_input.get("client_name", "")
    mandante_name = tool_input.get("mandante_name", "")

    cli = await client_repo.find_by_name_regex(user_id, client_name)
    if not cli:
        return {"error": f"Cliente '{client_name}' non trovato nel CRM."}

    mand = await mandante_repo.find_by_name_regex(user_id, mandante_name)
    if not mand:
        return {"error": f"Mandante '{mandante_name}' non trovato nel CRM."}

    items = await resolve_line_items(product_repo, tool_input, user_id, mand["id"], tool_input.get("title", "Vendita"))

    total = calc_offer_total(items)
    if total <= 0:
        return {"error": "L'importo della vendita deve essere maggiore di zero. Specifica un importo o dei prezzi validi."}

    accepted = bool(tool_input.get("accepted", False))
    sale_type = tool_input.get("sale_type", "nuovo")
    if sale_type not in ("nuovo", "rinnovo"):
        sale_type = "nuovo"
    title = tool_input.get("title") or f"Vendita {cli['company_name']}"

    return {
        "tool_name": "add_offer",
        "summary": {
            "client_name": cli["company_name"],
            "mandante_name": mand["name"],
            "title": title,
            "amount": total,
            "status": "accettata" if accepted else "bozza",
            "sale_type": sale_type,
        },
        "resolved_input": {
            "client_id": cli["id"], "client_name": cli["company_name"],
            "mandante_id": mand["id"], "mandante_name": mand["name"],
            "title": title, "items": items, "amount": total,
            "accepted": accepted, "sale_type": sale_type,
        },
    }


async def finalize_offer(offer_repo, mandante_repo, user_id: str, resolved: dict) -> str:
    """Scrive davvero l'offerta/vendita sul DB, a partire da un
    resolved_input già risolto da prepare_add_offer (eventualmente
    modificato dall'utente nella scheda di conferma, es. importo).
    Il payload può arrivare anche direttamente da /api/ai/execute-action,
    quindi va validato di nuovo qui: non ci si può fidare che sia sempre
    passato prima da prepare_add_offer."""
    items = resolved.get("items") or []
    # Difesa in profondità: anche se items arriva già "pulito" da
    # prepare_add_offer, ri-sanitizziamo quantità/prezzi prima di scrivere,
    # nel caso il payload arrivi direttamente dall'endpoint di conferma.
    items = [
        {
            "product_id": it.get("product_id"),
            "description": it.get("description", "Vendita"),
            "quantity": max(_safe_float(it.get("quantity"), 1), 0.01),
            "unit_price": max(_safe_float(it.get("unit_price"), 0), 0),
            "discount": max(_safe_float(it.get("discount"), 0), 0),
        }
        for it in items
    ]
    amount = resolved.get("amount")
    title = resolved.get("title") or "Vendita"
    # Se l'utente ha modificato l'importo in fase di conferma rispetto a
    # quello calcolato dai prodotti, sostituiamo gli item con una riga
    # unica coerente col nuovo importo, invece di lasciare un totale che
    # non corrisponde più alla somma delle righe originali.
    if amount is not None and amount != "":
        amount_f = _safe_float(amount, None)
        if amount_f is not None and (not items or round(calc_offer_total(items), 2) != round(amount_f, 2)):
            items = [{"product_id": None, "description": title, "quantity": 1, "unit_price": amount_f, "discount": 0}]

    total = calc_offer_total(items)
    if total <= 0:
        return "❌ L'importo deve essere maggiore di zero: vendita non registrata."

    accepted = bool(resolved.get("accepted", False))
    status = "accettata" if accepted else "bozza"
    sale_type = resolved.get("sale_type", "nuovo")
    if sale_type not in ("nuovo", "rinnovo"):
        sale_type = "nuovo"

    mand = await mandante_repo.find_one(resolved["mandante_id"], user_id)
    if not mand:
        return "❌ Mandante non più trovato nel CRM."

    offer_doc = {
        "id": gen_id(), "user_id": user_id,
        "client_id": resolved["client_id"], "mandante_id": resolved["mandante_id"],
        "title": title, "items": items, "total": total,
        "expires_at": None, "status": status, "sale_type": sale_type, "notes": "",
        "created_at": now_iso(),
    }
    await offer_repo.insert(offer_doc)

    msg = f"✅ Vendita registrata: {resolved.get('client_name','')} - {mand['name']} - €{total:.2f} ({sale_type}), stato: {status}."

    if accepted:
        order = await order_service.create_from_offer({"id": user_id}, offer_doc)
        rate = get_commission_rate(mand, sale_type)
        comm_amount = round(order.get("total", 0) * rate / 100, 2)
        msg += f" Ordine registrato e provvigione generata: €{comm_amount:.2f} ({rate}%)."

    return msg
