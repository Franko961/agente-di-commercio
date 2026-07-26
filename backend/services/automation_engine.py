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
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from core.config import AUTOMATION_MAX_ATTEMPTS, AUTOMATION_ENGINE_INTERVAL_SECONDS
from core.observability import record_event
from core.utils import gen_id, now_iso, now_local
from repositories.automation_repository import automation_repository
from repositories.automation_run_repository import automation_run_repository
from repositories.automation_notification_repository import automation_notification_repository
from repositories.client_repository import client_repository
from repositories.offer_repository import offer_repository
from repositories.lead_repository import lead_repository
from repositories.appointment_repository import appointment_repository
from repositories.user_repository import user_repository
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
        user_repo=user_repository,
        send_email_fn=send_email,
    ):
        self.automation_repo = automation_repo
        self.run_repo = run_repo
        self.notification_repo = notification_repo
        self.client_repo = client_repo
        self.offer_repo = offer_repo
        self.lead_repo = lead_repo
        self.appointment_repo = appointment_repo
        self.user_repo = user_repo
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

        executed = skipped = errors = 0
        for target_type, target_id, context in candidates:
            try:
                should_run = await self._should_run(aid, target_id, config)
                if not should_run:
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

    async def _should_run(self, automation_id: str, target_id: str, config: dict) -> bool:
        """Dedup: non rieseguire per la stessa entità se già eseguita con
        successo, a meno che sia passato config['cooldown_days'] dall'ultima
        esecuzione (utile per promemoria che si vogliono ripetere, es. un
        lead ancora inattivo una settimana dopo). Un'esecuzione fallita ma
        sotto la soglia di tentativi va invece sempre ritentata."""
        prev = await self.run_repo.find_one(automation_id, target_id)
        if not prev:
            return True
        if prev.get("status") == "error":
            return True  # ritenta finché non supera AUTOMATION_MAX_ATTEMPTS
        if prev.get("status") == "failed_permanent":
            return False
        # status == "ok": rieseguito solo se è stato configurato un cooldown
        # ed è già trascorso.
        cooldown_days = config.get("cooldown_days")
        if not cooldown_days:
            return False
        updated_at = _parse_iso(prev.get("updated_at"))
        if not updated_at:
            return True
        return datetime.now(timezone.utc) - updated_at >= timedelta(days=cooldown_days)

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
            # NOTA: il modello Lead non traccia un updated_at (nessun campo
            # "ultima interazione"), quindi created_at è l'unico riferimento
            # disponibile per "inattività". Se in futuro si aggiunge un
            # updated_at aggiornato ad ogni cambio di stato/nota, va usato
            # quello al posto di created_at qui sotto.
            created_at = _parse_iso(lead.get("created_at"))
            if created_at and created_at <= threshold:
                out.append(("lead", lead["id"], lead))
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

        await self.send_email_fn(
            user.get("email", ""),
            f"🔔 SALESFLY — {title}",
            f"<p>{message}</p>",
        )

    async def _action_create_task(self, automation: dict, target_type: str, target_id: str, context: dict) -> None:
        user = await self._get_user(automation["user_id"])
        if not user or user.get("is_demo"):
            return  # non scrive appuntamenti reali sull'account demo condiviso

        from services.appointment_service import appointment_service
        from models.appointment import AppointmentIn

        client_id = target_id if target_type == "client" else context.get("client_id")
        start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
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
        sent = await self.send_email_fn(to, subject, f"<p>{body_text}</p>")
        if not sent:
            raise RuntimeError("Invio email fallito (vedi log email_service)")


def _describe_target(target_type: str, context: dict) -> str:
    if target_type == "offer":
        return f"Offerta \"{context.get('title', '')}\" (scadenza {context.get('expires_at', '')[:10]})"
    if target_type == "client":
        return f"Cliente \"{context.get('company_name', '')}\""
    if target_type == "lead":
        return f"Lead \"{context.get('company_name', '')}\""
    return target_type


_TRIGGER_EVALUATORS = {
    "offer_expiring": AutomationEngine._eval_offer_expiring,
    "no_visit_30d": AutomationEngine._eval_no_visit_30d,
    "lead_inactive": AutomationEngine._eval_lead_inactive,
}

_ACTION_EXECUTORS = {
    "send_reminder": AutomationEngine._action_send_reminder,
    "create_task": AutomationEngine._action_create_task,
    "send_email": AutomationEngine._action_send_email,
}

automation_engine = AutomationEngine()
