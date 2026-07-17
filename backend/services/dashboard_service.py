from datetime import datetime, timezone, timedelta
from typing import Dict
from core.database import db


class DashboardService:
    async def get_stats(self, user: dict) -> dict:
        clients = await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        offers = await db.offers.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        leads = await db.leads.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        appts = await db.appointments.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        commissions = await db.commissions.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        expenses = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)

        revenue_won = sum(o.get("total", 0) for o in offers if o.get("status") == "accettata")
        revenue_pipeline = sum(o.get("total", 0) for o in offers if o.get("status") in ("inviata", "bozza"))
        accrued = sum(c.get("amount", 0) for c in commissions if c.get("status") == "maturato")
        collected = sum(c.get("amount", 0) for c in commissions if c.get("status") == "incassato")

        # Revenue by zone
        by_zone: Dict[str, float] = {}
        for o in offers:
            if o.get("status") != "accettata":
                continue
            cli = next((c for c in clients if c["id"] == o.get("client_id")), None)
            if cli:
                zone = cli.get("zone") or "N/D"
                by_zone[zone] = by_zone.get(zone, 0) + o.get("total", 0)

        # Clienti per settore merceologico
        by_sector: Dict[str, int] = {}
        for c in clients:
            sector = c.get("sector") or "Non specificato"
            by_sector[sector] = by_sector.get(sector, 0) + 1

        # Monthly revenue (last 6 months) from accepted offers
        months: Dict[str, float] = {}
        for o in offers:
            if o.get("status") != "accettata":
                continue
            ca = o.get("created_at", "")
            if len(ca) >= 7:
                key = ca[:7]
                months[key] = months.get(key, 0) + o.get("total", 0)
        monthly = sorted(
            [{"month": k, "revenue": round(v, 2)} for k, v in months.items()],
            key=lambda m: m["month"],
        )[-6:]

        # Monthly expenses by category (last 6 months) — per grafico a barre impilate
        exp_monthly_by_cat: Dict[str, Dict[str, float]] = {}
        for e in expenses:
            d = e.get("date", "")
            if len(d) >= 7:
                key = d[:7]
                cat = e.get("category") or "altro"
                exp_monthly_by_cat.setdefault(key, {})
                exp_monthly_by_cat[key][cat] = exp_monthly_by_cat[key].get(cat, 0) + e.get("amount", 0)
        exp_months = {k: sum(v.values()) for k, v in exp_monthly_by_cat.items()}
        expenses_monthly = []
        for month_key in sorted(exp_monthly_by_cat.keys())[-6:]:
            row = {"month": month_key, "total": round(exp_months[month_key], 2)}
            row.update({cat: round(amt, 2) for cat, amt in exp_monthly_by_cat[month_key].items()})
            expenses_monthly.append(row)

        # Expenses by category
        exp_by_category: Dict[str, float] = {}
        for e in expenses:
            cat = e.get("category") or "altro"
            exp_by_category[cat] = exp_by_category.get(cat, 0) + e.get("amount", 0)
        expenses_by_category = sorted(
            [{"category": k, "amount": round(v, 2)} for k, v in exp_by_category.items()],
            key=lambda x: -x["amount"],
        )

        # Upcoming appointments (next 7 days)
        today = datetime.now(timezone.utc)
        week_later = today + timedelta(days=7)
        upcoming = []
        for a in appts:
            try:
                start = datetime.fromisoformat(a["start"].replace("Z", "+00:00"))
                if today <= start <= week_later and a.get("status") == "pianificato":
                    upcoming.append(a)
            except Exception:
                pass

        # Goal: monthly target = 10000
        current_month_key = today.strftime("%Y-%m")
        current_month_rev = months.get(current_month_key, 0)
        current_month_expenses = exp_months.get(current_month_key, 0)
        goal = 10000

        return {
            "kpi": {
                "clients_count": len(clients),
                "leads_count": len(leads),
                "offers_count": len(offers),
                "revenue_won": round(revenue_won, 2),
                "revenue_pipeline": round(revenue_pipeline, 2),
                "commissions_accrued": round(accrued, 2),
                "commissions_collected": round(collected, 2),
                "current_month_revenue": round(current_month_rev, 2),
                "monthly_goal": goal,
                "goal_pct": round(min(100, (current_month_rev / goal) * 100) if goal else 0, 1),
                "expenses_total": round(sum(e.get("amount", 0) for e in expenses), 2),
                "current_month_expenses": round(current_month_expenses, 2),
            },
            "by_zone": [{"zone": k, "revenue": round(v, 2)} for k, v in by_zone.items()],
            "by_sector": sorted([{"sector": k, "count": v} for k, v in by_sector.items()], key=lambda x: -x["count"]),
            "monthly": monthly,
            "expenses_monthly": expenses_monthly,
            "expenses_by_category": expenses_by_category,
            "upcoming_appointments": upcoming[:10],
            "pipeline": {
                "nuovo": sum(1 for l in leads if l.get("status") == "nuovo"),
                "contattato": sum(1 for l in leads if l.get("status") == "contattato"),
                "qualificato": sum(1 for l in leads if l.get("status") == "qualificato"),
                "trattativa": sum(1 for l in leads if l.get("status") == "trattativa"),
                "vinto": sum(1 for l in leads if l.get("status") == "vinto"),
                "perso": sum(1 for l in leads if l.get("status") == "perso"),
            },
        }


dashboard_service = DashboardService()
