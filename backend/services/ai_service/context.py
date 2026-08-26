from datetime import datetime, timezone
from typing import Dict

from core.utils import now_local, local_month_str
from services.commission_service import normalize_manual_commission


async def gather_context(
    client_repo, offer_repo, appointment_repo, commission_repo, manual_commission_repo, expense_repo, user_id: str
) -> str:
    clients = await client_repo.find_many(user_id, {})
    offers = await offer_repo.find_many(user_id)
    appts = await appointment_repo.find_many(user_id)
    commissions = await commission_repo.find_many(user_id)
    # Le provvigioni inserite manualmente contano come vere anche nel
    # briefing AI, non solo nella pagina Provvigioni — vedi
    # normalize_manual_commission per il perché di created_at sintetico.
    manual_commissions = await manual_commission_repo.find_many(user_id)
    commissions = commissions + [normalize_manual_commission(user_id, m) for m in manual_commissions]
    expenses = await expense_repo.find_many(user_id)

    # Clients with no recent visit
    today = datetime.now(timezone.utc)
    last_visit_map: Dict[str, datetime] = {}
    for a in appts:
        try:
            d = datetime.fromisoformat(a["start"].replace("Z", "+00:00"))
            cid = a.get("client_id")
            if cid and (cid not in last_visit_map or d > last_visit_map[cid]):
                last_visit_map[cid] = d
        except Exception:
            pass

    summary = []
    summary.append(f"Numero clienti: {len(clients)}, offerte: {len(offers)}, appuntamenti: {len(appts)}")
    summary.append("\nClienti (max 20):")
    for c in clients[:20]:
        last = last_visit_map.get(c["id"])
        days_ago = (today - last).days if last else "mai"
        summary.append(f"- {c['company_name']} ({c.get('zone','')}, potenziale {c.get('potential','medio')}) ultima visita: {days_ago}gg")
    summary.append("\nOfferte recenti:")
    for o in offers[-10:]:
        summary.append(f"- {o.get('title')} importo {o.get('total',0)}€ stato {o.get('status')}")

    # Provvigioni: i dati venivano già recuperati sopra ma non erano mai
    # inclusi nel riepilogo — l'assistente non aveva quindi visibilità
    # sulla situazione provvigionale dell'utente nel contesto generale
    # (solo tramite un tool dedicato, se invocato esplicitamente).
    current_month_key = now_local().strftime("%Y-%m")
    accrued = sum(c.get("amount", 0) for c in commissions if c.get("status") == "maturato")
    collected = sum(c.get("amount", 0) for c in commissions if c.get("status") == "incassato")
    month_commissions = [c for c in commissions if local_month_str(c.get("created_at")) == current_month_key]
    total_month_commissions = sum(c.get("amount", 0) for c in month_commissions)
    summary.append(
        f"\nProvvigioni — maturate non incassate: {round(accrued,2)}€, incassate: {round(collected,2)}€, "
        f"totale mese corrente: {round(total_month_commissions,2)}€ ({len(month_commissions)} voci)"
    )
    summary.append("Provvigioni recenti (max 10):")
    for c in commissions[-10:]:
        summary.append(
            f"- {c.get('sale_type','')} {c.get('amount',0)}€ stato {c.get('status')}"
            + (f" (bonus scaglione {c['bonus_tier_threshold']}€)" if c.get("sale_type") == "bonus" else "")
        )

    current_month = now_local().strftime("%Y-%m")
    month_expenses = [e for e in expenses if (e.get("date") or "").startswith(current_month)]
    total_month_expenses = sum(e.get("amount", 0) for e in month_expenses)
    summary.append(f"\nSpese del mese corrente: {round(total_month_expenses,2)}€ ({len(month_expenses)} voci)")
    summary.append("Spese recenti (max 10):")
    for e in expenses[-10:]:
        summary.append(f"- {e.get('date')} {e.get('category')} {e.get('amount',0)}€ {e.get('description','')}".strip())

    return "\n".join(summary)
