import calendar
import logging
import math
from datetime import datetime, timezone, timedelta, date
from typing import Dict, Optional
from core.database import db
from core.utils import now_local, local_date_str, local_month_str
from services.settings_service import DEFAULT_GOAL_REVENUE
from services.commission_service import normalize_manual_commission

logger = logging.getLogger(__name__)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distanza in linea d'aria tra due coordinate (km). Usata per una stima
    approssimativa dei km di oggi, non un percorso stradale reale."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _focus_reason_text(focus: dict) -> str:
    """Motivo in linguaggio naturale per cui il briefing propone questo
    cliente — SEMPRE onesto rispetto a cosa sappiamo davvero: mai un
    riferimento al traffico stradale, che l'app non ha modo di conoscere
    (il pianificatore giro visite usa OpenRouteService/stima in linea
    d'aria, non dati di traffico in tempo reale, vedi route_optimization_service)."""
    reason = focus.get("reason")
    if reason == "expiry_and_inactivity":
        days = focus.get("days_since_last_order")
        return f"ha un'offerta in scadenza a breve e non fa un ordine da {days} giorni"
    if reason == "expiry_only":
        return "ha un'offerta in scadenza a breve"
    days = focus.get("days_since_last_visit")
    if days is not None:
        return f"non lo visiti da {days} giorni"
    return "non lo visiti da molto tempo"


def _pluralize_it(count: int, singular: str, plural: str, none_label: Optional[str] = None) -> str:
    """Restituisce una stringa tipo '5 clienti da richiamare', gestendo i
    casi 0/1/N in italiano. Se none_label è dato, viene usato al posto di
    '0 ...' quando count è zero (es. 'Nessun appuntamento in programma'),
    per non produrre frasi innaturali come '0 clienti da richiamare'."""
    if count == 0 and none_label:
        return none_label
    noun = singular if count == 1 else plural
    return f"{count} {noun}"


class DashboardService:
    # Soglia di guardia per il .to_list(5000) usato in get_stats/get_today_brief:
    # se una collection di un utente la supera, i record oltre questo numero
    # spariscono silenziosamente dai calcoli — meglio saperlo dai log che da
    # un utente che segnala numeri sballati. Non blocca nulla, è solo un
    # segnale che la strategia "carica tutto e calcola in Python" ha bisogno
    # di essere rivista (aggregation pipeline) per quell'utente/collection.
    _CAP_WARNING_THRESHOLD = 4000

    @staticmethod
    def _warn_if_near_cap(user_id: str, **collections) -> None:
        for name, docs in collections.items():
            if len(docs) >= DashboardService._CAP_WARNING_THRESHOLD:
                logger.warning(
                    f"dashboard_service: utente {user_id} ha {len(docs)} record in "
                    f"'{name}', vicino/oltre la cap di 5000 usata in .to_list() — "
                    f"dati oltre 5000 vengono esclusi dai calcoli."
                )

    async def get_stats(self, user: dict, mandante_id: Optional[str] = None) -> dict:
        clients = await db.clients.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        offers = await db.offers.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        leads = await db.leads.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        appts = await db.appointments.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        commissions = await db.commissions.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        expenses = await db.expenses.find({"user_id": user["id"]}, {"_id": 0}).to_list(5000)
        self._warn_if_near_cap(user["id"], clients=clients, offers=offers, leads=leads,
                                appointments=appts, commissions=commissions, expenses=expenses)

        # Le provvigioni inserite manualmente contano come provvigioni vere:
        # unite qui, PRIMA del filtro mandante sotto, così una manuale senza
        # mandante_id viene esclusa quando è attivo un mandante specifico
        # (stessa regola già in vigore per quelle reali, riusata gratis).
        manual_commissions = await db.manual_commissions.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
        commissions = commissions + [normalize_manual_commission(user["id"], m) for m in manual_commissions]

        # Filtro per mandante attivo. Leads e Spese non hanno ancora un
        # collegamento al mandante (per le spese serve una migrazione di
        # schema, non ancora fatta) e restano quindi sempre a livello
        # generale, indipendentemente dal mandante selezionato.
        if mandante_id:
            clients = [c for c in clients if mandante_id in (c.get("mandante_ids") or [])]
            client_ids = {c["id"] for c in clients}
            offers = [o for o in offers if o.get("mandante_id") == mandante_id]
            commissions = [c for c in commissions if c.get("mandante_id") == mandante_id]
            appts = [a for a in appts if a.get("client_id") in client_ids]

        revenue_won = sum(o.get("total", 0) for o in offers if o.get("status") == "accettata")
        revenue_pipeline = sum(o.get("total", 0) for o in offers if o.get("status") in ("inviata", "bozza"))
        accrued = sum(c.get("amount", 0) for c in commissions if c.get("status") == "maturato")
        collected = sum(c.get("amount", 0) for c in commissions if c.get("status") == "incassato")

        # Mappa per lookup O(1) del cliente per id, invece di scandire l'intera
        # lista clients per ogni offerta (che sarebbe O(offers × clients)).
        clients_by_id = {c["id"]: c for c in clients}

        # Revenue by zone
        by_zone: Dict[str, float] = {}
        for o in offers:
            if o.get("status") != "accettata":
                continue
            cli = clients_by_id.get(o.get("client_id"))
            if cli:
                zone = cli.get("zone") or "N/D"
                by_zone[zone] = by_zone.get(zone, 0) + o.get("total", 0)

        # Clienti per settore merceologico
        by_sector: Dict[str, int] = {}
        for c in clients:
            sector = c.get("sector") or "Non specificato"
            by_sector[sector] = by_sector.get(sector, 0) + 1

        # Monthly revenue (last 6 months) from accepted offers.
        # local_month_str converte created_at (UTC) nel mese di calendario in
        # ora italiana — affettare direttamente created_at[:7] attribuirebbe
        # al mese sbagliato le offerte accettate nell'ora dopo la mezzanotte
        # italiana, finché l'orologio UTC non ha ancora girato di giorno/mese.
        months: Dict[str, float] = {}
        for o in offers:
            if o.get("status") != "accettata":
                continue
            key = local_month_str(o.get("created_at"))
            if key:
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

        # Upcoming appointments (next 7 days). Qui "today"/"week_later" sono
        # istanti UTC usati solo per un confronto di intervallo (today <=
        # start <= week_later): corretto così, il fuso orario non conta per
        # un confronto tra istanti.
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

        # Obiettivi mensili: configurabili dall'utente in Impostazioni (vedi
        # settings_service). Solo il fatturato ha un default di fallback per
        # compatibilità con chi non l'ha ancora impostato — le altre tre
        # metriche restano "non impostate" (None) finché l'utente non le
        # configura, per non mostrare percentuali fuorvianti su un obiettivo
        # mai scelto.
        goal_revenue = user.get("goal_revenue") if user.get("goal_revenue") is not None else DEFAULT_GOAL_REVENUE
        goal_commissions = user.get("goal_commissions")
        goal_new_clients = user.get("goal_new_clients")
        goal_visits = user.get("goal_visits")

        # "Mese corrente" va stabilito in ora italiana, non UTC: altrimenti,
        # tra la mezzanotte italiana e il momento in cui anche l'orologio UTC
        # gira (1-2 ore, a seconda di CET/CEST), fatturato/provvigioni/nuovi
        # clienti del "oggi" vengono attribuiti ancora al giorno/mese
        # precedente. Vedi core/utils.now_local per i dettagli.
        current_month_key = now_local().strftime("%Y-%m")
        current_month_rev = months.get(current_month_key, 0)
        current_month_expenses = exp_months.get(current_month_key, 0)

        # Provvigioni maturate questo mese (per l'obiettivo provvigioni)
        commissions_month = sum(
            c.get("amount", 0) for c in commissions
            if local_month_str(c.get("created_at")) == current_month_key
        )

        # Nuovi clienti acquisiti questo mese (per l'obiettivo nuovi clienti)
        new_clients_month = sum(
            1 for c in clients if local_month_str(c.get("created_at")) == current_month_key
        )

        # Visite (appuntamenti completati) effettuate questo mese, in base
        # alla data dell'appuntamento (non a quando è stato creato il record)
        visits_month = sum(
            1 for a in appts
            if a.get("status") == "completato" and local_month_str(a.get("start")) == current_month_key
        )

        def _pct(current, goal):
            if not goal:
                return None
            return round(min(100, (current / goal) * 100), 1)

        goal_pct = _pct(current_month_rev, goal_revenue)

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
                "monthly_goal": goal_revenue,
                "goal_pct": goal_pct if goal_pct is not None else 0,
                "expenses_total": round(sum(e.get("amount", 0) for e in expenses), 2),
                "current_month_expenses": round(current_month_expenses, 2),
                # Le tre metriche sotto sono None finché l'utente non imposta
                # il relativo obiettivo in Impostazioni — il frontend mostra
                # la barra di progresso solo quando *_goal non è None.
                "commissions_month": round(commissions_month, 2),
                "commissions_goal": goal_commissions,
                "commissions_goal_pct": _pct(commissions_month, goal_commissions),
                "new_clients_month": new_clients_month,
                "new_clients_goal": goal_new_clients,
                "new_clients_goal_pct": _pct(new_clients_month, goal_new_clients),
                "visits_month": visits_month,
                "visits_goal": goal_visits,
                "visits_goal_pct": _pct(visits_month, goal_visits),
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

    async def get_today_brief(self, user: dict, mandante_id: Optional[str] = None) -> dict:
        """Riepilogo operativo della giornata per la home della dashboard:
        appuntamenti, clienti da richiamare, offerte in scadenza, pagamenti da
        verificare, km stimati e obiettivo del giorno, più un suggerimento
        (calcolato, non generato dall'AI a ogni caricamento per rapidità/costo)
        su quale cliente visitare per primo."""
        user_id = user["id"]
        clients = await db.clients.find({"user_id": user_id}, {"_id": 0}).to_list(5000)
        appts = await db.appointments.find({"user_id": user_id}, {"_id": 0}).to_list(5000)
        offers = await db.offers.find({"user_id": user_id}, {"_id": 0}).to_list(5000)
        commissions = await db.commissions.find({"user_id": user_id}, {"_id": 0}).to_list(5000)
        orders = await db.orders.find({"user_id": user_id}, {"_id": 0}).to_list(5000)
        self._warn_if_near_cap(user_id, clients=clients, appointments=appts, offers=offers,
                                commissions=commissions, orders=orders)

        # Le provvigioni inserite manualmente contano come provvigioni vere
        # anche qui (payments_to_verify sotto) — vedi commento gemello in
        # get_stats.
        manual_commissions = await db.manual_commissions.find({"user_id": user_id}, {"_id": 0}).to_list(500)
        commissions = commissions + [normalize_manual_commission(user_id, m) for m in manual_commissions]

        # Stesso filtro per mandante attivo usato in get_stats.
        if mandante_id:
            clients = [c for c in clients if mandante_id in (c.get("mandante_ids") or [])]
            client_ids = {c["id"] for c in clients}
            offers = [o for o in offers if o.get("mandante_id") == mandante_id]
            commissions = [c for c in commissions if c.get("mandante_id") == mandante_id]
            orders = [o for o in orders if o.get("mandante_id") == mandante_id]
            appts = [a for a in appts if a.get("client_id") in client_ids]

        now = datetime.now(timezone.utc)
        # "Oggi" va stabilito in ora italiana: vedi la nota su
        # current_month_key in get_stats / core/utils.now_local per il
        # perché. `now` (UTC) resta invece l'istante corretto per tutti i
        # confronti aritmetici più sotto (start_dt >= now, giorni trascorsi, ecc.).
        today_local = now_local()
        today_str = today_local.strftime("%Y-%m-%d")
        clients_by_id = {c["id"]: c for c in clients}

        # Appuntamenti pianificati per oggi. local_date_str converte lo
        # start (UTC) nel suo giorno di calendario in ora italiana, invece di
        # affettare direttamente la stringa UTC (che per un'ora o due dopo la
        # mezzanotte italiana darebbe il giorno sbagliato).
        todays_appts = sorted(
            (a for a in appts if local_date_str(a.get("start")) == today_str and a.get("status") == "pianificato"),
            key=lambda a: a.get("start", ""),
        )

        # Prossimo appuntamento pianificato (oggi o nei giorni successivi),
        # in minuti da adesso: usato dal briefing AI proattivo (es. "tra 40
        # minuti"). Considera anche appuntamenti futuri oltre oggi, non solo
        # quelli odierni, cercando semplicemente il primo con start >= ora.
        # Avvolto in try/except: un dato imprevisto qui non deve mai far
        # fallire l'intero riepilogo (dashboard "Oggi" + briefing AI).
        next_appointment_minutes = None
        next_appointment_client = None
        try:
            upcoming_appts = sorted(
                (a for a in appts if a.get("status") == "pianificato" and a.get("start")),
                key=lambda a: a["start"],
            )
            for a in upcoming_appts:
                try:
                    start_dt = datetime.fromisoformat(a["start"].replace("Z", "+00:00"))
                    is_next = start_dt >= now
                except Exception:
                    # Copre sia un formato data non valido, sia il caso di un
                    # appuntamento con 'start' salvato come datetime "naive"
                    # (senza fuso orario): confrontarlo con `now` (aware)
                    # solleva TypeError, non ValueError, quindi va incluso
                    # anche qui e non solo nel parsing.
                    continue
                if is_next:
                    next_appointment_minutes = round((start_dt - now).total_seconds() / 60)
                    cli = clients_by_id.get(a.get("client_id"))
                    next_appointment_client = cli.get("company_name") if cli else None
                    break
        except Exception as e:
            logger.error(f"get_today_brief: errore calcolo next_appointment: {e}")

        # Ultima visita (qualsiasi appuntamento passato) per cliente
        last_appt_by_client: Dict[str, datetime] = {}
        for a in appts:
            cid = a.get("client_id")
            if not cid:
                continue
            try:
                d = datetime.fromisoformat(a["start"].replace("Z", "+00:00"))
                is_past = d <= now
            except Exception:
                continue
            if is_past and (cid not in last_appt_by_client or d > last_appt_by_client[cid]):
                last_appt_by_client[cid] = d

        # Clienti da richiamare: nessuna visita negli ultimi 21 giorni (o mai)
        CALLBACK_DAYS = 21
        clients_to_call = 0
        for c in clients:
            if c.get("status") == "inattivo":
                continue
            last = last_appt_by_client.get(c["id"])
            days = (now - last).days if last else None
            if days is None or days >= CALLBACK_DAYS:
                clients_to_call += 1

        # Clienti inattivi da tempo: nessuna visita negli ultimi 60 giorni (o
        # mai). Soglia distinta e più ampia di CALLBACK_DAYS: non è "va
        # richiamato a breve" ma "è a rischio abbandono", usata dal briefing
        # AI proattivo.
        INACTIVE_DAYS = 60
        inactive_clients_60d = 0
        try:
            for c in clients:
                if c.get("status") == "inattivo":
                    continue
                last = last_appt_by_client.get(c["id"])
                days = (now - last).days if last else None
                if days is None or days >= INACTIVE_DAYS:
                    inactive_clients_60d += 1
        except Exception as e:
            logger.error(f"get_today_brief: errore calcolo inactive_clients_60d: {e}")

        # Offerte in scadenza nei prossimi 7 giorni (ancora aperte)
        week_ahead = now + timedelta(days=7)
        offers_expiring = []
        for o in offers:
            if o.get("status") not in ("bozza", "inviata"):
                continue
            exp = o.get("expires_at")
            if not exp:
                continue
            try:
                exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                is_expiring_soon = now <= exp_dt <= week_ahead
            except Exception:
                continue
            if is_expiring_soon:
                offers_expiring.append({**o, "_expires_dt": exp_dt})

        # Pagamenti da verificare: provvigioni maturate ma non ancora incassate
        payments_to_verify = sum(1 for c in commissions if c.get("status") == "maturato")

        # Km previsti oggi: distanza in linea d'aria tra gli appuntamenti di
        # oggi, in ordine di orario (solo se i clienti hanno coordinate salvate)
        coords = []
        for a in todays_appts:
            cli = clients_by_id.get(a.get("client_id"))
            if cli and cli.get("lat") is not None and cli.get("lng") is not None:
                coords.append((cli["lat"], cli["lng"]))
        km_today = None
        if len(coords) >= 2:
            km_today = round(
                sum(_haversine_km(*coords[i], *coords[i + 1]) for i in range(len(coords) - 1)), 1
            )

        # Obiettivo di oggi: quota residua del target mensile spalmata sui
        # giorni lavorativi (lun-ven) rimanenti nel mese, oggi incluso.
        # goal_revenue è quello configurato dall'utente in Impostazioni, con
        # lo stesso fallback usato in get_stats per chi non l'ha ancora impostato.
        goal_revenue = user.get("goal_revenue") if user.get("goal_revenue") is not None else DEFAULT_GOAL_REVENUE
        current_month_key = today_local.strftime("%Y-%m")
        month_revenue = sum(
            o.get("total", 0) for o in offers
            if o.get("status") == "accettata" and local_month_str(o.get("created_at")) == current_month_key
        )
        _, days_in_month = calendar.monthrange(today_local.year, today_local.month)
        remaining_working_days = sum(
            1 for d in range(today_local.day, days_in_month + 1)
            if date(today_local.year, today_local.month, d).weekday() < 5
        ) or 1
        daily_goal = round(max(goal_revenue - month_revenue, 0) / remaining_working_days, 2)

        # Previsione fatturato di fine mese: proiezione lineare "a ritmo
        # attuale" (fatturato fatto finora / giorni trascorsi * giorni totali
        # del mese). Semplice e trasparente, non una stima statistica
        # sofisticata: comunica un ordine di grandezza, non una certezza.
        try:
            elapsed_days = max(today_local.day, 1)
            revenue_forecast_month = round(month_revenue / elapsed_days * days_in_month, 2)
        except Exception as e:
            logger.error(f"get_today_brief: errore calcolo revenue_forecast_month: {e}")
            revenue_forecast_month = None

        # Suggerimento: priorità di visita per oggi (cliente con offerta in
        # scadenza + più tempo senza ordini, altrimenti cliente più trascurato)
        last_order_by_client: Dict[str, datetime] = {}
        for o in orders:
            cid = o.get("client_id")
            ca = o.get("created_at")
            if not cid or not ca:
                continue
            try:
                d = datetime.fromisoformat(ca.replace("Z", "+00:00"))
                is_newer = cid not in last_order_by_client or d > last_order_by_client[cid]
            except Exception:
                continue
            if is_newer:
                last_order_by_client[cid] = d

        nearest_expiry_by_client: Dict[str, dict] = {}
        for o in offers_expiring:
            cid = o.get("client_id")
            if not cid:
                continue
            if cid not in nearest_expiry_by_client or o["_expires_dt"] < nearest_expiry_by_client[cid]["_expires_dt"]:
                nearest_expiry_by_client[cid] = o

        def _pick_focus_client(eligible_ids: Optional[set] = None) -> Optional[dict]:
            """Sceglie il cliente da segnalare come priorità (offerta in
            scadenza + più tempo senza ordini, altrimenti il più trascurato).
            eligible_ids, se dato, restringe la scelta a un sottoinsieme di
            clienti (es. solo quelli con una visita in programma oggi) —
            usato per il suggerimento "inizia da X" del briefing, che non ha
            senso su un cliente che oggi non si visita comunque."""
            best, best_days = None, -1
            for cid, offer in nearest_expiry_by_client.items():
                if eligible_ids is not None and cid not in eligible_ids:
                    continue
                cli = clients_by_id.get(cid)
                if not cli:
                    continue
                last_order = last_order_by_client.get(cid)
                days_since_order = (now - last_order).days if last_order else None
                rank = days_since_order if days_since_order is not None else 9999
                if rank > best_days:
                    best_days = rank
                    best = {
                        "client_id": cid,
                        "client_name": cli.get("company_name"),
                        "days_since_last_order": days_since_order,
                        "offer_title": offer.get("title"),
                        "offer_expires_at": offer.get("expires_at"),
                        "reason": "expiry_and_inactivity" if days_since_order and days_since_order >= 14 else "expiry_only",
                    }
            if best:
                return best

            most_neglected, max_days = None, -1
            for c in clients:
                if eligible_ids is not None and c["id"] not in eligible_ids:
                    continue
                if c.get("status") == "inattivo":
                    continue
                last = last_appt_by_client.get(c["id"])
                days = (now - last).days if last else 9999
                if days > max_days:
                    max_days, most_neglected = days, c
            if most_neglected and max_days >= CALLBACK_DAYS:
                return {
                    "client_id": most_neglected["id"],
                    "client_name": most_neglected.get("company_name"),
                    "days_since_last_order": None,
                    "days_since_last_visit": None if max_days == 9999 else max_days,
                    "offer_title": None,
                    "offer_expires_at": None,
                    "reason": "inactivity_only",
                }
            return None

        focus_client = _pick_focus_client()
        # Priorità ristretta ai clienti che hanno DAVVERO una visita in
        # programma oggi: consigliare di "iniziare da" un cliente che non è
        # nemmeno tra le visite odierne non avrebbe senso nel briefing.
        todays_client_ids = {a["client_id"] for a in todays_appts if a.get("client_id")}
        todays_focus_client = (
            _pick_focus_client(todays_client_ids) if todays_client_ids else None
        )

        # Fatturato "potenziale" se si chiudessero anche tutte le offerte in
        # scadenza mostrate sopra: non una previsione, solo un incentivo
        # concreto ("chiudine 2 e arrivi al 96%"), calcolato sul fatturato
        # già fatto questo mese (non sulla previsione lineare, che è già di
        # per sé una stima — sommarne un'altra sopra renderebbe il numero
        # meno difendibile).
        offers_expiring_total = round(sum(o.get("total", 0) for o in offers_expiring), 2)
        projected_pct_if_expiring_closed = None
        if offers_expiring_total > 0 and goal_revenue:
            projected_pct_if_expiring_closed = round(
                (month_revenue + offers_expiring_total) / goal_revenue * 100
            )

        return {
            "date": today_str,
            "appointments_today": len(todays_appts),
            "clients_to_call": clients_to_call,
            "offers_expiring": len(offers_expiring),
            "payments_to_verify": payments_to_verify,
            "km_today": km_today,
            "daily_goal": daily_goal,
            "focus_client": focus_client,
            "todays_focus_client": todays_focus_client,
            "next_appointment_minutes": next_appointment_minutes,
            "next_appointment_client": next_appointment_client,
            "inactive_clients_60d": inactive_clients_60d,
            "month_revenue_so_far": round(month_revenue, 2),
            "revenue_forecast_month": revenue_forecast_month,
            "monthly_goal": goal_revenue,
            "offers_expiring_total": offers_expiring_total,
            "projected_pct_if_expiring_closed": projected_pct_if_expiring_closed,
        }

    def format_morning_briefing(self, brief: dict, user_name: Optional[str] = None) -> str:
        """Trasforma il riepilogo calcolato da get_today_brief in un saluto
        proattivo in italiano ("Buongiorno Franco. Hai: ...") per l'apertura
        della pagina Assistente AI. Puramente calcolato dai dati già
        aggregati da get_today_brief: nessuna chiamata al modello, stesso
        principio di rapidità/costo zero già documentato lì."""
        saluto = f"Buongiorno {user_name}." if user_name else "Buongiorno."
        lines = [saluto, ""]

        visits = brief.get("appointments_today", 0)
        if visits == 0:
            lines.append("Oggi non hai visite in programma.")
        else:
            lines.append(f"Oggi hai {visits} visit{'a' if visits == 1 else 'e'} in programma.")

        todays_focus = brief.get("todays_focus_client")
        if todays_focus:
            lines.append(f"Ti consiglio di iniziare da {todays_focus['client_name']}: {_focus_reason_text(todays_focus)}.")

        lines += ["", "Hai:", ""]

        lines.append("✓ " + _pluralize_it(
            brief["clients_to_call"], "cliente da richiamare", "clienti da richiamare",
            none_label="Nessun cliente da richiamare al momento",
        ))
        lines.append("✓ " + _pluralize_it(
            brief["offers_expiring"], "offerta in scadenza", "offerte in scadenza",
            none_label="Nessuna offerta in scadenza nei prossimi giorni",
        ))

        mins = brief.get("next_appointment_minutes")
        if mins is not None:
            client_part = f" con {brief['next_appointment_client']}" if brief.get("next_appointment_client") else ""
            if mins <= 0:
                lines.append(f"✓ Appuntamento{client_part} in corso o appena iniziato")
            elif mins < 60:
                lines.append(f"✓ Prossimo appuntamento{client_part} tra {mins} minuti")
            else:
                hours, rem = divmod(mins, 60)
                time_str = f"{hours}h" + (f" {rem}min" if rem else "")
                lines.append(f"✓ Prossimo appuntamento{client_part} tra {time_str}")
        else:
            lines.append("✓ Nessun appuntamento in programma")

        lines.append("✓ " + _pluralize_it(
            brief["payments_to_verify"], "provvigione da controllare", "provvigioni da controllare",
            none_label="Nessuna provvigione da controllare",
        ))
        lines.append("✓ " + _pluralize_it(
            brief["inactive_clients_60d"], "cliente inattivo da oltre 60 giorni",
            "clienti inattivi da oltre 60 giorni",
            none_label="Nessun cliente inattivo da oltre 60 giorni",
        ))

        forecast = brief.get("revenue_forecast_month")
        goal = brief.get("monthly_goal")
        if forecast is not None and goal:
            if abs(forecast - goal) <= goal * 0.05:
                trend = "in linea con"
            elif forecast > goal:
                trend = "sopra"
            else:
                trend = "sotto"
            forecast_str = f"{forecast:,.0f}".replace(",", ".")
            goal_str = f"{goal:,.0f}".replace(",", ".")
            lines.append(f"✓ Previsione fatturato mese: €{forecast_str} ({trend} l'obiettivo di €{goal_str})")

        pct = brief.get("projected_pct_if_expiring_closed")
        n_expiring = brief.get("offers_expiring", 0)
        if pct is not None and n_expiring > 0:
            offerte_str = "l'offerta in scadenza" if n_expiring == 1 else f"le {n_expiring} offerte in scadenza"
            lines.append("")
            lines.append(f"Se chiudi {offerte_str} raggiungeresti il {pct}% dell'obiettivo mensile.")

        return "\n".join(lines)


dashboard_service = DashboardService()
