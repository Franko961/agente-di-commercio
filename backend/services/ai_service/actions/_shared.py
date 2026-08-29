from services.ai_service.catalog import _safe_float


async def resolve_line_items(
    product_repo,
    tool_input: dict,
    user_id: str,
    mandante_id: str,
    fallback_description: str,
) -> list:
    """Risolve product_names/quantities/unit_prices in righe con id
    prodotto risolto (o una riga singola da total_amount se i prodotti
    non sono noti). Condivisa da prepare_add_offer e prepare_add_order:
    stessa identica logica di risoluzione, cambia solo chi la chiama."""
    product_names = tool_input.get("product_names") or []
    quantities = tool_input.get("quantities") or []
    unit_prices = tool_input.get("unit_prices") or []

    items = []
    if product_names:
        for i, pname in enumerate(product_names):
            prod = await product_repo.find_by_name_regex(user_id, mandante_id, pname)
            qty = _safe_float(quantities[i] if i < len(quantities) else None, 1)
            if qty <= 0:
                qty = 1
            default_price = prod.get("price", 0) if prod else 0
            price = _safe_float(
                unit_prices[i] if i < len(unit_prices) else None, default_price
            )
            if price < 0:
                price = default_price
            items.append(
                {
                    "product_id": prod["id"] if prod else None,
                    "description": prod["name"] if prod else pname,
                    "quantity": qty,
                    "unit_price": price,
                    "discount": 0,
                }
            )
    else:
        total_amount = _safe_float(tool_input.get("total_amount"), 0)
        items.append(
            {
                "product_id": None,
                "description": fallback_description,
                "quantity": 1,
                "unit_price": total_amount,
                "discount": 0,
            }
        )
    return items
