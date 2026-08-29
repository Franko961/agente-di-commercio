from datetime import datetime, timezone
from typing import Dict

from core.utils import local_month_str


async def search_clients(
    client_repo, order_repo, appointment_repo, tool_input: dict, user_id: str
) -> str:
    """Filtra i clienti del CRM con criteri precisi (ultimo ordine,
    mese di visita, zona, potenziale). A differenza di gather_context
    (che tronca a 20 clienti per stare nel prompt), qui si scorre
    SEMPRE l'elenco completo: serve per rispondere in modo esatto a
    domande come 'clienti che non acquistano da tre mesi', non solo
    a colpo d'occhio sui più recenti."""
    clients = await client_repo.find_many(user_id, {})
    orders = await order_repo.find_many(user_id)
    appts = await appointment_repo.find_many(user_id)

    min_days = tool_input.get("min_days_since_last_order")
    visited_month = tool_input.get("visited_month")
    zone = tool_input.get("zone")
    potential = tool_input.get("potential")

    now = datetime.now(timezone.utc)

    last_order_by_client: Dict[str, datetime] = {}
    for o in orders:
        cid = o.get("client_id")
        ca = o.get("created_at")
        if not cid or not ca:
            continue
        try:
            d = datetime.fromisoformat(ca.replace("Z", "+00:00"))
        except Exception:
            continue
        if cid not in last_order_by_client or d > last_order_by_client[cid]:
            last_order_by_client[cid] = d

    visited_in_month = set()
    if visited_month:
        for a in appts:
            cid = a.get("client_id")
            # local_month_str converte start (UTC) nel mese di
            # calendario in ora italiana, come altrove — vedi
            # core/utils.now_local per il perché.
            if cid and local_month_str(a.get("start")) == visited_month:
                visited_in_month.add(cid)

    results = []
    for c in clients:
        if zone and (c.get("zone") or "").strip().lower() != zone.strip().lower():
            continue
        if potential and c.get("potential") != potential:
            continue
        if min_days is not None:
            last = last_order_by_client.get(c["id"])
            days_since = (now - last).days if last else None
            # Nessun ordine mai (days_since is None) soddisfa sempre il
            # filtro "non acquista da almeno N giorni".
            if days_since is not None and days_since < min_days:
                continue
        if visited_month and c["id"] not in visited_in_month:
            continue
        results.append(c)

    if not results:
        return "Nessun cliente trovato con questi criteri."

    lines = [f"Trovati {len(results)} clienti:"]
    MAX_LISTED = 30
    for c in results[:MAX_LISTED]:
        last = last_order_by_client.get(c["id"])
        last_txt = f"ultimo ordine {(now - last).days}gg fa" if last else "mai ordinato"
        zone_txt = c.get("zone") or "zona non specificata"
        lines.append(f"- {c['company_name']} ({zone_txt}, {last_txt})")
    if len(results) > MAX_LISTED:
        lines.append(f"... e altri {len(results) - MAX_LISTED} clienti.")
    return "\n".join(lines)


async def search_offers(offer_repo, tool_input: dict, user_id: str) -> str:
    """Filtra le offerte/vendite del CRM con criteri precisi (importo
    min/max, stato). A differenza di gather_context (che mostra solo le
    ultime 10), qui si scorre SEMPRE l'elenco completo."""
    offers = await offer_repo.find_many(user_id)

    min_amount = tool_input.get("min_amount")
    max_amount = tool_input.get("max_amount")
    status = tool_input.get("status")

    results = []
    for o in offers:
        total = o.get("total", 0)
        if min_amount is not None and total < min_amount:
            continue
        if max_amount is not None and total > max_amount:
            continue
        if status and o.get("status") != status:
            continue
        results.append(o)

    if not results:
        return "Nessuna offerta trovata con questi criteri."

    results.sort(key=lambda o: o.get("total", 0), reverse=True)
    lines = [f"Trovate {len(results)} offerte:"]
    MAX_LISTED = 30
    for o in results[:MAX_LISTED]:
        lines.append(
            f"- {o.get('title', 'Senza titolo')}: €{o.get('total', 0):.2f} ({o.get('status')})"
        )
    if len(results) > MAX_LISTED:
        lines.append(f"... e altre {len(results) - MAX_LISTED} offerte.")
    return "\n".join(lines)
