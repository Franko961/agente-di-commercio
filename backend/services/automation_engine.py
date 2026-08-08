"""Motore di esecuzione delle automazioni.

Il modello/servizio/router delle automazioni (models.automation,
services.automation_service, repositories.automation_repository) gestiscono
solo il CRUD della regola: nome, trigger, azione, config, enabled. Questo
modulo è il pezzo che mancava — chiamato periodicamente da
services.startup_service — e che:

  1. scorre le automazioni ATTIVE di tutti gli utenti;
  2. per ognuna, valuta la condizione del trigger (offer_expiring,
     no_visit_30d, lead_inactive) e produce la lista delle entità che la
     soddisfano oggi (un'offerta, un cliente, un lead...);
  3. per ogni entità, verifica in automation_runs se è già stata eseguita
     (dedup: la stessa automazione non spara due volte per la stessa
     entità, a meno che config.cooldown_days non ne richieda la ripetizione
     dopo N giorni);
  4. esegue l'azione (send_reminder, create_task, send_email), registra
     l'esito (ok/errore + tentativi) e aggiorna last_run_at/last_run_status
     sull'automazione stessa.

In più, tre opzioni facoltative in 'config', lette solo se presenti (in
assenza si comporta esattamente come prima):
  - 'email_subject'/'email_message': testo personalizzato per l'oggetto/il
    corpo dell'email, con placeholder {nome}/{scadenza}/{citta} sostituiti
    con i dati reali del cliente/offerta/lead coinvolto (vedi _render_template).
  - 'run_at' ("HH:MM"): valuta la regola una sola volta al giorno, nella
    finestra di ciclo più vicina a quell'orario, invece che ad ogni ciclo
    (vedi _matches_schedule).

Tutto avvolto in try/except a grana fine: un'automazione o un'entità che
falliscono non devono mai interrompere il ciclo delle altre.
"""
import html
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from core.config import AUTOMATION_MAX_ATTEMPTS, AUTOMATION_ENGINE_INTERVAL_SECONDS
from core.observability import record_event
from core.utils import gen_id, now_iso, now_local, local_wallclock_to_utc_iso, local_month_str, local_date_str
from repositories.automation_repository import automation_repository
from repositories.automation_run_repository import automation_run_repository
from repositories.automation_notification_repository import automation_notification_repository
from repositories.client_repository import client_repository
from repositories.offer_repository import offer_repository
from repositories.lead_repository import lead_repository
from repositories.appointment_repository import appointment_repository
from repositories.order_repository import order_repository
from repositories.commission_repository import commission_repository
from repositories.manual_commission_repository import manual_commission_repository
from repositories.user_repository import user_repository
from repositories.vehicle_deadline_repository import vehicle_deadline_repository
from repositories.employee_repository import employee_repository
from repositories.attendance_repository import attendance_repository
from repositories.leave_request_repository import leave_request_repository
from services.commission_service import normalize_manual_commission
from services.email_service import send_email

logger = logging.getLogger(__name__)

# Stati di offerta per cui una scadenza imminente ha ancora senso di essere
# segnalata: un'offerta già accettata/rifiutata/scaduta non è più "in corso".
_OPEN_OFFER_STATUSES = ("bozza", "inviata")
# Stati di lead considerati "chiusi": non ha senso avvisare che un lead vinto
# o perso è "inattivo".
_CLOSED_LEAD_STATUSES = ("vinto", "perso")


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


class _SafeDict(dict):
    """Usato con str.format_map: un placeholder sconosciuto (es. un typo
    dell'utente tipo '{nom}') viene lasciato letterale nel testo invece di
    far fallire l'invio con un KeyError — un errore di battitura nel
    contenuto personalizzato non deve mai bloccare un'automazione."""
    def __missing__(self, key):
        return "{" + key + "}"


def _placeholder_values(target_type: str, context: dict) -> dict:
    """Valori disponibili per il testo personalizzato di oggetto/messaggio
    (config['email_subject']/config['email_message']): {nome}, {scadenza}
    (solo per le offerte), {citta} (solo per clienti/lead)."""
    if target_type == "offer":
        return {"nome": context.get("title", ""), "scadenza": (context.get("expires_at") or "")[:10], "citta": ""}
    if target_type in ("client", "lead"):
        return {"nome": context.get("company_name", ""), "scadenza": "", "citta": context.get("city", "")}
    if target_type == "employee_attendance":
        nome = f"{context.get('name', '')} {context.get('surname', '')}".strip()
        return {"nome": nome, "scadenza": "", "citta": ""}
    return {"nome": "", "scadenza": "", "citta": ""}


def _render_template(template: str, target_type: str, context: dict) -> str:
    try:
        return template.format_map(_SafeDict(_placeholder_values(target_type, context)))
    except Exception:
        # Un template scritto male (es. una graffa spaiata) non deve mai far
        # fallire l'invio: meglio il testo grezzo che nessun invio.
        return template


def _matches_schedule(config: dict) -> bool:
    """Se config['run_at'] (formato 'HH:MM') è impostato, la regola viene
    valutata una sola volta al giorno, nel ciclo la cui finestra copre
    quell'orario — non ad ogni ciclo come le regole senza orario impostato.
    La finestra di tolleranza è ampia quanto l'intervallo tra due cicli
    (AUTOMATION_ENGINE_INTERVAL_SECONDS), così un solo ciclo al giorno vi
    ricade, indipendentemente da micro-scarti nell'istante esatto in cui
    il loop si sveglia."""
    run_at = config.get("run_at")
    if not run_at:
        return True
    try:
        hour_str, minute_str = run_at.split(":")
        target_minutes = int(hour_str) * 60 + int(minute_str)
    except (ValueError, AttributeError):
        return True  # config malformata: non bloccare l'automazione per questo

    now = now_local()
    now_minutes = now.hour * 60 + now.minute
    window_minutes = max(1, AUTOMATION_ENGINE_INTERVAL_SECONDS // 60)
    return 0 <= (now_minutes - target_minutes) % (24 * 60) < window_minutes


class AutomationEngine:
    def __init__(
        self,
        automation_repo=automation_repository,
        run_repo=automation_run_repository,
        notification_repo=automation_notification_repository,
        client_repo=client_repository,
        offer_repo=offer_repository,
        lead_repo=lead_repository,
        appointment_repo=appointment_repository,
        order_repo=order_repository,
        commission_repo=commission_repository,
        manual_commission_repo=manual_commission_repository,
        user_repo=user_repository,
        vehicle_deadline_repo=vehicle_deadline_repository,
        employee_repo=employee_repository,
        attendance_repo=attendance_repository,
        leave_request_repo=leave_request_repository,
        send_email_fn=send_email,
    ):
        self.automation_repo = automation_repo
        self.run_repo = run_repo
        self.notification_repo = notification_repo
        self.client_repo = client_repo
        self.offer_repo = offer_repo
        self.lead_repo = lead_repo
        self.appointment_repo = appointment_repo
        self.order_repo = order_repo
        self.commission_repo = commission_repo
        self.manual_commission_repo = manual_commission_repo
        self.user_repo = user_repo
        self.vehicle_deadline_repo = vehicle_deadline_repo
        self.employee_repo = employee_repo
        self.attendance_repo = attendance_repo
        self.leave_request_repo = leave_request_repo
        self.send_email_fn = send_email_fn

    # ------------------------------------------------------------------
    # Ciclo principale
    # ------------------------------------------------------------------
    async def run_cycle(self) -> dict:
        """Esegue un intero ciclo di valutazione. Ritorna un piccolo
        riepilogo (utile per i log e per i test), non solleva mai
        eccezioni verso il chiamante: ogni errore di singola automazione o
        singola entità viene isolato."""
        summary = {"automations": 0, "executed": 0, "skipped": 0, "errors": 0}
        automations = await self.automation_repo.find_all_enabled()

        for automation in automations:
            summary["automations"] += 1
            try:
                result = await self._run_automation(automation)
                summary["executed"] += result["executed"]
                summary["skipped"] += result["skipped"]
                summary["errors"] += result["errors"]
            except Exception as e:
                # Un'automazione mal configurata (trigger/azione sconosciuti,
                # config malformata) non deve bloccare le altre.
                logger.error(f"Automazione {automation.get('id')} fallita per errore inatteso: {e}")
                await record_event("automation_run", "failure", automation_id=automation.get("id"), error=str(e)[:300])
                summary["errors"] += 1

        return summary

    async def _run_automation(self, automation: dict) -> dict:
        aid = automation["id"]
        user_id = automation["user_id"]
        trigger = automation.get("trigger")
        action = automation.get("action")
        config = automation.get("config") or {}

        if not _matches_schedule(config):
            # Fuori dalla finestra oraria configurata (config['run_at']):
            # non valutata affatto in questo ciclo, e last_run_at NON viene
            # toccato — altrimenti l'interfaccia mostrerebbe "eseguita 10
            # minuti fa" ad ogni ciclo anche quando la regola non è stata
            # davvero valutata.
            return {"executed": 0, "skipped": 0, "errors": 0}

        evaluator = _TRIGGER_EVALUATORS.get(trigger)
        if not evaluator:
            logger.warning(f"Automazione {aid}: trigger sconosciuto '{trigger}', ignorata")
            await self.automation_repo.update_last_run(aid, {
                "last_run_at": now_iso(), "last_run_status": "error",
                "last_run_error": f"trigger sconosciuto: {trigger}",
                "last_run_executed": 0, "last_run_skipped": 0, "last_run_errors": 1,
            })
            return {"executed": 0, "skipped": 0, "errors": 1}

        if action not in _ACTION_EXECUTORS:
            logger.warning(f"Automazione {aid}: azione sconosciuta '{action}', ignorata")
            await self.automation_repo.update_last_run(aid, {
                "last_run_at": now_iso(), "last_run_status": "error",
                "last_run_error": f"azione sconosciuta: {action}",
                "last_run_executed": 0, "last_run_skipped": 0, "last_run_errors": 1,
            })
            return {"executed": 0, "skipped": 0, "errors": 1}

        candidates = await evaluator(self, user_id, config)
        cooldown_days = config.get("cooldown_days")

        executed = skipped = errors = 0
        for target_type, target_id, context in candidates:
            try:
                # Prenotazione atomica PRIMA di eseguire l'azione (vedi
                # AutomationRunRepository.try_claim): con più repliche del
                # backend in esecuzione contemporaneamente, un controllo
                # separato dall'esecuzione lascerebbe una finestra in cui
                # entrambe potrebbero superarlo ed eseguire due volte
                # l'azione (due email, due appuntamenti...) prima che una
                # delle due registri il risultato. Solo l'istanza che vince
                # questa prenotazione procede.
                claimed = await self.run_repo.try_claim(aid, user_id, target_type, target_id, cooldown_days=cooldown_days)
                if not claimed:
                    skipped += 1
                    continue
                await _ACTION_EXECUTORS[action](self, automation, target_type, target_id, context)
                await self.run_repo.upsert(aid, user_id, target_type, target_id, {
                    "status": "ok", "attempts": 0, "last_error": None, "updated_at": now_iso(),
                })
                await record_event("automation_run", "success", automation_id=aid, trigger=trigger, action=action)
                executed += 1
            except Exception as e:
                prev = await self.run_repo.find_one(aid, target_id)
                attempts = (prev.get("attempts", 0) if prev else 0) + 1
                status = "error" if attempts < AUTOMATION_MAX_ATTEMPTS else "failed_permanent"
                await self.run_repo.upsert(aid, user_id, target_type, target_id, {
                    "status": status, "attempts": attempts, "last_error": str(e)[:500], "updated_at": now_iso(),
                })
                await record_event("automation_run", "failure", automation_id=aid, trigger=trigger, action=action, error=str(e)[:300])
                logger.error(f"Automazione {aid} fallita su {target_type} {target_id} (tentativo {attempts}): {e}")
                errors += 1

        await self.automation_repo.update_last_run(aid, {
            "last_run_at": now_iso(),
            "last_run_status": "error" if errors else "ok",
            "last_run_error": None if not errors else f"{errors} esecuzione/i fallita/e nell'ultimo ciclo",
            "last_run_executed": executed,
            "last_run_skipped": skipped,
            "last_run_errors": errors,
        })
        return {"executed": executed, "skipped": skipped, "errors": errors}

    # ------------------------------------------------------------------
    # Valutatori di trigger — ognuno ritorna una lista di tuple
    # (target_type, target_id, context) dove context sono i dati già
    # caricati dell'entità, per non doverla ricaricare nell'executor.
    # ------------------------------------------------------------------
    async def _eval_offer_expiring(self, user_id: str, config: dict) -> list:
        days_before = config.get("days_before", 3)
        today = now_local().date()
        offers = await self.offer_repo.find_many(user_id)
        out = []
        for o in offers:
            if o.get("status") not in _OPEN_OFFER_STATUSES:
                continue
            expires_at = _parse_iso(o.get("expires_at"))
            if not expires_at:
                continue
            days_left = (expires_at.date() - today).days
            if 0 <= days_left <= days_before:
                out.append(("offer", o["id"], o))
        return out

    async def _eval_no_visit_30d(self, user_id: str, config: dict) -> list:
        days = config.get("days", 30)
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        clients = await self.client_repo.find_many(user_id, {})
        appointments = await self.appointment_repo.find_many(user_id)

        last_visit_by_client: dict = {}
        for a in appointments:
            if a.get("status") == "annullato" or not a.get("client_id"):
                continue
            start = _parse_iso(a.get("start"))
            if not start or start > datetime.now(timezone.utc):
                continue  # un appuntamento futuro non è ancora una "visita avvenuta"
            cid = a["client_id"]
            if cid not in last_visit_by_client or start > last_visit_by_client[cid]:
                last_visit_by_client[cid] = start

        out = []
        for c in clients:
            last_visit = last_visit_by_client.get(c["id"])
            if last_visit is None:
                # Nessuna visita mai registrata: usa la data di creazione del
                # cliente come riferimento, per non segnalare come "non
                # visitato da 30 giorni" un cliente appena inserito.
                last_visit = _parse_iso(c.get("created_at"))
            if last_visit and last_visit <= threshold:
                out.append(("client", c["id"], c))
        return out

    async def _eval_lead_inactive(self, user_id: str, config: dict) -> list:
        days = config.get("days", 7)
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        leads = await self.lead_repo.find_many(user_id)
        out = []
        for lead in leads:
            if lead.get("status") in _CLOSED_LEAD_STATUSES:
                continue
            # last_interaction_at viene aggiornato ad ogni modifica/cambio
            # di stato del lead (vedi lead_service.update_lead/update_status):
            # riflette la VERA ultima interazione, non solo quando è stato
            # creato. created_at resta come fallback solo per i lead creati
            # prima dell'introduzione di questo campo, che ne sono privi.
            last_activity = _parse_iso(lead.get("last_interaction_at")) or _parse_iso(lead.get("created_at"))
            if last_activity and last_activity <= threshold:
                out.append(("lead", lead["id"], lead))
        return out

    async def _eval_no_order_days(self, user_id: str, config: dict) -> list:
        """Cliente senza ordini da N giorni (default 90): stesso schema di
        _eval_no_visit_30d, ma sul repository ordini invece che appuntamenti —
        un cliente che non ordina da tempo è un segnale commerciale diverso
        (e spesso più urgente) di uno semplicemente non visitato."""
        days = config.get("days", 90)
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        clients = await self.client_repo.find_many(user_id, {})
        orders = await self.order_repo.find_many(user_id)

        last_order_by_client: dict = {}
        for o in orders:
            cid = o.get("client_id")
            created = _parse_iso(o.get("created_at"))
            if not cid or not created:
                continue
            if cid not in last_order_by_client or created > last_order_by_client[cid]:
                last_order_by_client[cid] = created

        out = []
        for c in clients:
            last_order = last_order_by_client.get(c["id"])
            if last_order is None:
                # Nessun ordine mai registrato: usa la data di creazione del
                # cliente come riferimento, per non segnalare come "senza
                # ordini da 90 giorni" un cliente inserito ieri.
                last_order = _parse_iso(c.get("created_at"))
            if last_order and last_order <= threshold:
                out.append(("client", c["id"], c))
        return out

    async def _eval_client_created(self, user_id: str, config: dict) -> list:
        """Nuovo cliente inserito: candidato per i clienti creati negli
        ultimi N giorni (default 2). La finestra serve solo a limitare la
        query e a evitare che l'attivazione della regola faccia scattare
        l'azione retroattivamente su TUTTO il portafoglio esistente — il
        dedup vero (una volta sola per cliente, per sempre) è comunque
        garantito da automation_runs, indipendentemente dalla finestra."""
        days = config.get("days", 2)
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        clients = await self.client_repo.find_many(user_id, {})
        out = []
        for c in clients:
            created = _parse_iso(c.get("created_at"))
            if created and created >= threshold:
                out.append(("client", c["id"], c))
        return out

    async def _eval_client_birthday(self, user_id: str, config: dict) -> list:
        """Compleanno cliente: confronta solo mese/giorno (l'anno di nascita
        salvato non conta ai fini del trigger). target_id include l'anno
        corrente ("<client_id>:<anno>") apposta: a differenza degli altri
        trigger, qui vogliamo che si ripeta ogni anno, non una sola volta per
        sempre — senza bisogno che l'utente configuri un cooldown_days per
        farlo funzionare correttamente."""
        days_before = config.get("days_before", 0)
        today = now_local().date()
        clients = await self.client_repo.find_many(user_id, {})
        out = []
        for c in clients:
            birthday = c.get("birthday")
            if not birthday:
                continue
            try:
                bday = datetime.strptime(birthday, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            # Prossimo compleanno nel calendario corrente (quest'anno, o
            # l'anno prossimo se è già passato) — per calcolare quanti giorni
            # mancano indipendentemente da quanto è vecchio l'anno salvato.
            try:
                next_bday = bday.replace(year=today.year)
            except ValueError:
                continue  # 29 febbraio in un anno non bisestile: nessun match quest'anno
            if next_bday < today:
                try:
                    next_bday = bday.replace(year=today.year + 1)
                except ValueError:
                    continue
            days_until = (next_bday - today).days
            if 0 <= days_until <= days_before:
                out.append(("client", f"{c['id']}:{next_bday.year}", c))
        return out

    async def _eval_tomorrow_appointments(self, user_id: str, config: dict) -> list:
        """Digest 'domani hai N visite': un solo invio aggregato al giorno,
        non uno per appuntamento. target_id include la data odierna apposta:
        così si ripete automaticamente ogni giorno (un giorno diverso = un
        target_id mai visto prima), senza bisogno di alcun cooldown."""
        tomorrow = (now_local() + timedelta(days=1)).strftime("%Y-%m-%d")
        appts = await self.appointment_repo.find_many(user_id)
        tomorrow_appts = [
            a for a in appts
            if a.get("status") == "pianificato" and local_date_str(a.get("start")) == tomorrow
        ]
        if not tomorrow_appts:
            return []

        clients = await self.client_repo.find_many(user_id, {})
        clients_by_id = {c["id"]: c for c in clients}
        client_names = [
            clients_by_id[a["client_id"]]["company_name"]
            for a in tomorrow_appts
            if a.get("client_id") in clients_by_id
        ]

        today_str = now_local().strftime("%Y-%m-%d")
        context = {"count": len(tomorrow_appts), "client_names": client_names}
        return [("digest_appointments", f"{user_id}:{today_str}", context)]

    async def _eval_commissions_below_target_mid_month(self, user_id: str, config: dict) -> list:
        """Digest 'provvigioni sotto obiettivo': valutato solo il giorno del
        mese configurato (default 15, check_day) — _matches_schedule copre
        solo l'orario, non il giorno del mese, quindi il controllo va fatto
        qui. Calcolo del fatturato provvigioni del mese volutamente NON
        riusa dashboard_service.get_stats (che aggrega molto di più: grafici
        per zona/settore/mese, pipeline...) per non appesantire ogni ciclo
        del motore con letture/calcoli che qui non servono — mirror solo
        della formula usata lì (stesso goal_commissions, stesso
        local_month_str)."""
        check_day = config.get("check_day", 15)
        if now_local().day != check_day:
            return []

        user = await self.user_repo.find_by_id(user_id)
        if not user:
            return []
        goal_commissions = user.get("goal_commissions")
        if not goal_commissions:
            return []  # nessun obiettivo provvigioni impostato: nulla da confrontare

        threshold_pct = config.get("threshold_pct", 50)
        current_month_key = now_local().strftime("%Y-%m")
        commissions = await self.commission_repo.find_many(user_id)
        # Le provvigioni manuali contano come vere anche qui, per lo stesso
        # motivo spiegato dove sono state introdotte nel briefing AI/dashboard.
        manual_commissions = await self.manual_commission_repo.find_many(user_id)
        commissions = commissions + [normalize_manual_commission(user_id, m) for m in manual_commissions]
        commissions_month = sum(
            c.get("amount", 0) for c in commissions
            if local_month_str(c.get("created_at")) == current_month_key
        )
        pct = (commissions_month / goal_commissions * 100) if goal_commissions else 0
        if pct >= threshold_pct:
            return []

        today_str = now_local().strftime("%Y-%m-%d")
        context = {
            "commissions_month": round(commissions_month, 2),
            "goal_commissions": goal_commissions,
            "pct": round(pct),
            "missing": round(goal_commissions - commissions_month, 2),
        }
        return [("digest_commissions", f"{user_id}:{today_str}", context)]

    async def _eval_vehicle_deadline(self, user_id: str, config: dict) -> list:
        """Scadenze documentali dei mezzi (assicurazione/revisione/bollo,
        vedi modulo Flotta) in arrivo tra esattamente una delle soglie
        configurate (default 7/15/30 giorni). target_id include la soglia
        ("<deadline_id>:<soglia>") apposta: ogni soglia deve generare il
        proprio promemoria indipendente in automation_runs, altrimenti la
        soglia più vicina (es. 7 giorni) risulterebbe già "consumata" da
        quella più lontana (30 giorni) sulla stessa scadenza."""
        reminder_days = config.get("reminder_days") or [7, 15, 30]
        deadlines = await self.vehicle_deadline_repo.find_many(user_id)
        today = now_local().date()
        out = []
        for d in deadlines:
            try:
                due = datetime.strptime(d["due_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            days_until = (due - today).days
            if days_until in reminder_days:
                out.append(("vehicle_deadline", f"{d['id']}:{days_until}", {**d, "days_until": days_until}))
        return out

    async def _eval_attendance_missing(self, user_id: str, config: dict) -> list:
        """Dipendente che non ha ancora timbrato l'ingresso oggi, pur
        essendo un giorno lavorativo per lui/lei ed essendo passata almeno
        un'ora dall'inizio del turno configurato (work_days/shift_start_time
        sulla scheda dipendente, vedi models.employee). Un dipendente SENZA
        questi due campi impostati non viene mai monitorato apposta: niente
        falsi allarmi retroattivi su chi non ha mai avuto un orario da
        rispettare. Le assenze approvate (ferie/permessi/malattia) che
        coprono la data odierna escludono il dipendente dal controllo.
        target_id include la data odierna apposta: si ripete da solo ogni
        giorno lavorativo, senza bisogno di alcun cooldown_days."""
        now = now_local()
        today_str = now.date().isoformat()
        weekday = now.weekday()  # 0 = lunedì ... 6 = domenica

        employees = await self.employee_repo.find_many(user_id)
        out = []
        for e in employees:
            if not e.get("active", True) or e.get("employment_status") != "attivo":
                continue
            work_days = e.get("work_days")
            shift_start = e.get("shift_start_time")
            if not work_days or not shift_start or weekday not in work_days:
                continue
            try:
                hour, minute = (int(p) for p in shift_start.split(":"))
            except (ValueError, AttributeError):
                continue  # orario malformato: non blocca il ciclo, semplicemente non monitorato
            threshold = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(hours=1)
            if now < threshold:
                continue

            sessions = await self.attendance_repo.find_many(e["id"], user_id)
            if any(local_date_str(s["clock_in"]) == today_str for s in sessions):
                continue  # ha già timbrato oggi (sessione aperta o chiusa)

            leave_requests = await self.leave_request_repo.find_by_employee(e["id"])
            if any(
                r["status"] == "approvata" and r["date_from"] <= today_str <= r["date_to"]
                for r in leave_requests
            ):
                continue  # assenza approvata che copre oggi: esclusa dal controllo

            out.append(("employee_attendance", f"{e['id']}:{today_str}", e))
        return out

    # ------------------------------------------------------------------
    # Esecutori di azione
    # ------------------------------------------------------------------
    async def _get_user(self, user_id: str) -> Optional[dict]:
        return await self.user_repo.find_by_id(user_id)

    async def _recipient_email_for(self, target_type: str, context: dict, user: dict) -> str:
        """Determina il destinatario di un'email di follow-up: il cliente o
        il lead coinvolto se ha un'email, altrimenti l'agente stesso."""
        if target_type == "offer":
            client = await self.client_repo.find_one(context.get("client_id"), context.get("user_id", ""))
            if client and client.get("email"):
                return client["email"]
        elif target_type == "client" and context.get("email"):
            return context["email"]
        elif target_type == "lead" and context.get("email"):
            return context["email"]
        return user.get("email", "")

    async def _action_send_reminder(self, automation: dict, target_type: str, target_id: str, context: dict) -> None:
        user = await self._get_user(automation["user_id"])
        if not user:
            raise RuntimeError("Utente dell'automazione non trovato")

        config = automation.get("config") or {}
        label = _describe_target(target_type, context)
        custom_subject = config.get("email_subject")
        custom_message = config.get("email_message")
        title = _render_template(custom_subject, target_type, context) if custom_subject else (automation.get("name") or "Promemoria automazione")
        message = _render_template(custom_message, target_type, context) if custom_message else f"{title}: {label}"

        await self.notification_repo.insert({
            "id": gen_id(), "user_id": automation["user_id"], "automation_id": automation["id"],
            "title": title, "message": message, "target_type": target_type, "target_id": target_id,
            "read": False, "created_at": now_iso(),
        })

        if user.get("is_demo"):
            return  # niente invii reali per l'account demo condiviso

        # Stessa ragione di _action_send_email: message può contenere dati
        # del CRM o il template configurato dall'utente, va HTML-escaped
        # prima di finire nel corpo dell'email.
        await self.send_email_fn(
            user.get("email", ""),
            f"🔔 SALESFLY — {title}",
            f"<p>{html.escape(message)}</p>",
        )

    async def _action_create_task(self, automation: dict, target_type: str, target_id: str, context: dict) -> None:
        user = await self._get_user(automation["user_id"])
        if not user or user.get("is_demo"):
            return  # non scrive appuntamenti reali sull'account demo condiviso

        from services.appointment_service import appointment_service
        from models.appointment import AppointmentIn

        # context["id"] invece di target_id per target_type=="client": per il
        # trigger compleanno target_id è composito ("<client_id>:<anno>", per
        # far ripetere l'automazione ogni anno — vedi _eval_client_birthday),
        # mentre context è sempre il documento cliente vero e proprio, il cui
        # "id" coincide con target_id per tutti gli altri trigger su cliente.
        client_id = context.get("id") if target_type == "client" else context.get("client_id")
        start = _next_task_datetime_utc_iso(automation.get("config") or {})
        payload = AppointmentIn(
            client_id=client_id,
            title=f"Follow-up: {automation.get('name') or 'automazione'}",
            description=_describe_target(target_type, context),
            start=start,
            status="pianificato",
        )
        await appointment_service.create_appointment(user, payload)

    async def _action_send_email(self, automation: dict, target_type: str, target_id: str, context: dict) -> None:
        user = await self._get_user(automation["user_id"])
        if not user:
            raise RuntimeError("Utente dell'automazione non trovato")
        if user.get("is_demo"):
            return

        to = await self._recipient_email_for(target_type, context, user)
        if not to:
            raise RuntimeError("Nessun indirizzo email disponibile per il destinatario")

        config = automation.get("config") or {}
        custom_subject = config.get("email_subject")
        custom_message = config.get("email_message")
        label = _describe_target(target_type, context)
        subject = _render_template(custom_subject, target_type, context) if custom_subject else (automation.get("name") or "Follow-up")
        body_text = _render_template(custom_message, target_type, context) if custom_message else label
        # body_text può contenere dati del CRM (nome cliente, titolo offerta,
        # ecc.) o il testo del template configurato dall'utente: va sempre
        # HTML-escaped prima di finire nel corpo dell'email, altrimenti un
        # valore con markup HTML/script verrebbe interpretato dal client di
        # posta del destinatario (che può essere anche un cliente reale,
        # non solo l'agente stesso) invece che mostrato come testo semplice
        # — stessa protezione già applicata in contact_request_service.py,
        # demo_request_service.py e auth_service.py.
        sent = await self.send_email_fn(to, subject, f"<p>{html.escape(body_text)}</p>")
        if not sent:
            raise RuntimeError("Invio email fallito (vedi log email_service)")


# Default per l'azione create_task: un orario lavorativo sensato invece
# dell'ora esatta in cui capita di girare il ciclo del motore, e un giorno
# di ritardo (domani) se non diversamente configurato.
_DEFAULT_TASK_TIME = "09:00"
_DEFAULT_TASK_DELAY_DAYS = 1


def _next_task_datetime_utc_iso(config: dict) -> str:
    """Calcola quando piazzare il task creato da 'create_task':
    config['task_delay_days'] giorni da oggi IN ORA ITALIANA (non UTC —
    altrimenti la mezzanotte italiana/UTC può far slittare il giorno di
    calcolo), alle config['task_time'] (default 09:00). Prima si usava
    semplicemente 'adesso in UTC + 24 ore', che produceva appuntamenti a
    qualunque orario capitasse di girare il ciclo (es. le 21:30 di notte)
    invece di un orario lavorativo scelto apposta."""
    task_time = config.get("task_time") or _DEFAULT_TASK_TIME
    task_delay_days = config.get("task_delay_days", _DEFAULT_TASK_DELAY_DAYS)

    try:
        hour, minute = (int(p) for p in task_time.split(":"))
    except (ValueError, AttributeError, TypeError):
        hour, minute = 9, 0  # config malformata: orario di default, mai un crash

    try:
        delay_days = int(task_delay_days)
    except (ValueError, TypeError):
        delay_days = _DEFAULT_TASK_DELAY_DAYS

    target_date = (now_local() + timedelta(days=delay_days)).date()
    local_wallclock = f"{target_date.isoformat()}T{hour:02d}:{minute:02d}:00"
    return local_wallclock_to_utc_iso(local_wallclock)


def _describe_target(target_type: str, context: dict) -> str:
    if target_type == "offer":
        return f"Offerta \"{context.get('title', '')}\" (scadenza {context.get('expires_at', '')[:10]})"
    if target_type == "client":
        return f"Cliente \"{context.get('company_name', '')}\""
    if target_type == "lead":
        return f"Lead \"{context.get('company_name', '')}\""
    if target_type == "digest_appointments":
        names = context.get("client_names") or []
        names_str = ", ".join(names[:5]) + (", ..." if len(names) > 5 else "")
        count = context.get("count", 0)
        tappe = "visita" if count == 1 else "visite"
        suffix = f": {names_str}" if names_str else ""
        return f"Domani hai {count} {tappe} in programma{suffix}"
    if target_type == "digest_commissions":
        return (
            f"Provvigioni totali al {context.get('pct', 0)}% dell'obiettivo mensile "
            f"— mancano €{context.get('missing', 0):,.0f}".replace(",", ".")
        )
    if target_type == "vehicle_deadline":
        labels = {"assicurazione": "Assicurazione", "revisione": "Revisione", "bollo": "Bollo", "altro": "Scadenza"}
        label = labels.get(context.get("type"), "Scadenza")
        return f"{label} di {context.get('vehicle_plate', '')} tra {context.get('days_until', '?')} giorni"
    if target_type == "employee_attendance":
        nome = f"{context.get('name', '')} {context.get('surname', '')}".strip()
        return f"{nome} non ha ancora timbrato l'ingresso oggi"
    return target_type


_TRIGGER_EVALUATORS = {
    "offer_expiring": AutomationEngine._eval_offer_expiring,
    "no_visit_30d": AutomationEngine._eval_no_visit_30d,
    "lead_inactive": AutomationEngine._eval_lead_inactive,
    "no_order_days": AutomationEngine._eval_no_order_days,
    "client_created": AutomationEngine._eval_client_created,
    "client_birthday": AutomationEngine._eval_client_birthday,
    "tomorrow_appointments": AutomationEngine._eval_tomorrow_appointments,
    "commissions_below_target_mid_month": AutomationEngine._eval_commissions_below_target_mid_month,
    "vehicle_deadline": AutomationEngine._eval_vehicle_deadline,
    "attendance_missing": AutomationEngine._eval_attendance_missing,
}

_ACTION_EXECUTORS = {
    "send_reminder": AutomationEngine._action_send_reminder,
    "create_task": AutomationEngine._action_create_task,
    "send_email": AutomationEngine._action_send_email,
}

automation_engine = AutomationEngine()
