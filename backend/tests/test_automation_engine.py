"""
Test per il motore di esecuzione delle automazioni (services.automation_engine).

Verifica che, a differenza del solo CRUD già esistente in
automation_service, le automazioni vengano davvero VALUTATE ED ESEGUITE:
condizione soddisfatta -> azione eseguita -> non rieseguita una seconda
volta per la stessa entità (dedup) -> un errore persistente smette di
essere ritentato dopo AUTOMATION_MAX_ATTEMPTS tentativi.

Usa repository finti in memoria (nessun MongoDB reale), stesso stile degli
altri test del progetto (vedi tests/test_ai_tool_forcing.py).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_automation_engine.py -v
"""
import sys
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, ".")

from services.automation_engine import AutomationEngine
from core.config import AUTOMATION_MAX_ATTEMPTS


def run(coro):
    return asyncio.run(coro)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _days_ago(n: float) -> str:
    return _iso(datetime.now(timezone.utc) - timedelta(days=n))


def _days_from_now(n: float) -> str:
    return _iso(datetime.now(timezone.utc) + timedelta(days=n))


# ---------- Repository finti ----------

class FakeAutomationRepo:
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_all_enabled(self):
        return [dict(d) for d in self.docs if d.get("enabled")]

    async def find_many(self, user_id):
        return [dict(d) for d in self.docs if d["user_id"] == user_id]

    async def update_last_run(self, aid, data):
        for d in self.docs:
            if d["id"] == aid:
                d.update(data)


class FakeRunRepo:
    def __init__(self):
        self.docs = {}
        self.claim_calls = 0

    def _key(self, automation_id, target_id):
        return (automation_id, target_id)

    async def find_one(self, automation_id, target_id):
        d = self.docs.get(self._key(automation_id, target_id))
        return dict(d) if d else None

    async def try_claim(self, automation_id, user_id, target_type, target_id, cooldown_days=None, stale_after_seconds=300):
        self.claim_calls += 1
        key = self._key(automation_id, target_id)
        now = datetime.now(timezone.utc)
        now_iso_str = now.isoformat()
        existing = self.docs.get(key)

        if existing is None:
            self.docs[key] = {
                "automation_id": automation_id, "user_id": user_id,
                "target_type": target_type, "target_id": target_id,
                "status": "processing", "attempts": 0, "last_error": None,
                "claimed_at": now_iso_str, "updated_at": now_iso_str,
            }
            return True

        status = existing.get("status")
        can_claim = False
        if status == "error":
            can_claim = True
        elif status == "processing":
            claimed_at = existing.get("claimed_at")
            if claimed_at and now - datetime.fromisoformat(claimed_at) >= timedelta(seconds=stale_after_seconds):
                can_claim = True
        elif status == "ok" and cooldown_days:
            updated_at = existing.get("updated_at")
            if updated_at and now - datetime.fromisoformat(updated_at) >= timedelta(days=cooldown_days):
                can_claim = True

        if can_claim:
            existing.update({"status": "processing", "claimed_at": now_iso_str, "updated_at": now_iso_str})
            return True
        return False

    async def upsert(self, automation_id, user_id, target_type, target_id, data):
        key = self._key(automation_id, target_id)
        existing = self.docs.get(key, {})
        existing.update({
            "automation_id": automation_id, "user_id": user_id,
            "target_type": target_type, "target_id": target_id, **data,
        })
        self.docs[key] = existing

    async def find_many_by_automation(self, automation_id, limit=200):
        return [dict(d) for d in self.docs.values() if d["automation_id"] == automation_id]

    async def delete_by_automation(self, automation_id):
        self.docs = {k: v for k, v in self.docs.items() if v["automation_id"] != automation_id}


class FakeNotificationRepo:
    def __init__(self):
        self.docs = []

    async def insert(self, doc):
        self.docs.append(doc)
        return doc

    async def find_many(self, user_id, unread_only=False, limit=100):
        return [d for d in self.docs if d["user_id"] == user_id]

    async def mark_read(self, nid, user_id):
        for d in self.docs:
            if d["id"] == nid and d["user_id"] == user_id:
                d["read"] = True


class FakeSimpleRepo:
    """Repo generico find_many/find_one su una lista fissa di dict — usato
    per client/offer/lead/appointment nei test."""
    def __init__(self, docs=None):
        self.docs = docs or []

    async def find_many(self, user_id, *args, **kwargs):
        return [dict(d) for d in self.docs if d.get("user_id") == user_id]

    async def find_one(self, doc_id, user_id=None):
        for d in self.docs:
            if d["id"] == doc_id:
                return dict(d)
        return None


class FakeUserRepo:
    def __init__(self, users):
        self.users = {u["id"]: u for u in users}

    async def find_by_id(self, uid):
        return dict(self.users[uid]) if uid in self.users else None


def build_engine(automations=None, offers=None, clients=None, leads=None,
                  appointments=None, orders=None, commissions=None,
                  users=None, send_email_fn=None):
    sent_emails = []

    async def default_send_email(to, subject, html):
        sent_emails.append({"to": to, "subject": subject, "html": html})
        return True

    engine = AutomationEngine(
        automation_repo=FakeAutomationRepo(automations or []),
        run_repo=FakeRunRepo(),
        notification_repo=FakeNotificationRepo(),
        client_repo=FakeSimpleRepo(clients or []),
        offer_repo=FakeSimpleRepo(offers or []),
        lead_repo=FakeSimpleRepo(leads or []),
        appointment_repo=FakeSimpleRepo(appointments or []),
        order_repo=FakeSimpleRepo(orders or []),
        commission_repo=FakeSimpleRepo(commissions or []),
        user_repo=FakeUserRepo(users or [{"id": "user-1", "email": "agente@example.com"}]),
        send_email_fn=send_email_fn or default_send_email,
    )
    engine._sent_emails = sent_emails
    return engine


# ---------- offer_expiring + send_reminder ----------

def test_offerta_in_scadenza_genera_promemoria_e_notifica():
    automations = [{
        "id": "auto-1", "user_id": "user-1", "name": "Promemoria scadenza",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 3},
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-1", "client_id": "c-1", "title": "Offerta Rossi",
        "status": "inviata", "expires_at": _days_from_now(2),
    }]
    engine = build_engine(automations=automations, offers=offers)

    summary = run(engine.run_cycle())

    assert summary == {"automations": 1, "executed": 1, "skipped": 0, "errors": 0}
    assert len(engine.notification_repo.docs) == 1
    assert engine.notification_repo.docs[0]["target_id"] == "offer-1"
    assert len(engine._sent_emails) == 1
    assert engine._sent_emails[0]["to"] == "agente@example.com"


def test_offerta_non_in_scadenza_non_genera_nulla():
    automations = [{
        "id": "auto-1", "user_id": "user-1", "name": "Promemoria scadenza",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 3},
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-1", "client_id": "c-1", "title": "Offerta lontana",
        "status": "inviata", "expires_at": _days_from_now(20),
    }]
    engine = build_engine(automations=automations, offers=offers)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0
    assert engine.notification_repo.docs == []


def test_offerta_gia_accettata_viene_ignorata():
    automations = [{
        "id": "auto-1", "user_id": "user-1", "name": "Promemoria scadenza",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 3},
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-1", "client_id": "c-1", "title": "Offerta chiusa",
        "status": "accettata", "expires_at": _days_from_now(1),
    }]
    engine = build_engine(automations=automations, offers=offers)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


# ---------- Dedup: stessa entità non rieseguita due volte ----------

def test_stessa_offerta_non_genera_due_promemoria_in_due_cicli():
    automations = [{
        "id": "auto-1", "user_id": "user-1", "name": "Promemoria scadenza",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 3},
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-1", "client_id": "c-1", "title": "Offerta Rossi",
        "status": "inviata", "expires_at": _days_from_now(2),
    }]
    engine = build_engine(automations=automations, offers=offers)

    first = run(engine.run_cycle())
    second = run(engine.run_cycle())

    assert first["executed"] == 1
    assert second["executed"] == 0
    assert second["skipped"] == 1
    assert len(engine._sent_emails) == 1  # non due


def test_cooldown_permette_di_ripetere_il_promemoria_dopo_n_giorni():
    automations = [{
        "id": "auto-1", "user_id": "user-1", "name": "Promemoria ricorrente",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 10, "cooldown_days": 5},
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-1", "client_id": "c-1", "title": "Offerta Rossi",
        "status": "inviata", "expires_at": _days_from_now(9),
    }]
    engine = build_engine(automations=automations, offers=offers)

    run(engine.run_cycle())
    # Forza l'ultima esecuzione a 6 giorni fa (> cooldown di 5): deve ripartire.
    key = ("auto-1", "offer-1")
    engine.run_repo.docs[key]["updated_at"] = _days_ago(6)

    second = run(engine.run_cycle())

    assert second["executed"] == 1
    assert len(engine._sent_emails) == 2


# ---------- no_visit_30d + create_task ----------

def test_cliente_non_visitato_da_30_giorni_crea_task(monkeypatch):
    automations = [{
        "id": "auto-2", "user_id": "user-1", "name": "Cliente non visitato",
        "trigger": "no_visit_30d", "action": "create_task", "enabled": True,
        "config": {},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Srl", "created_at": _days_ago(200)}]
    appointments = [{
        "id": "a-1", "user_id": "user-1", "client_id": "c-1",
        "status": "completato", "start": _days_ago(45),
    }]
    engine = build_engine(automations=automations, clients=clients, appointments=appointments)

    created = []

    class FakeAppointmentService:
        async def create_appointment(self, user, payload):
            created.append(payload)
            return {"id": "new-appt"}

    import services.appointment_service as appt_mod
    monkeypatch.setattr(appt_mod, "appointment_service", FakeAppointmentService())

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    assert len(created) == 1
    assert created[0].client_id == "c-1"


def test_cliente_visitato_di_recente_non_genera_task():
    automations = [{
        "id": "auto-2", "user_id": "user-1", "name": "Cliente non visitato",
        "trigger": "no_visit_30d", "action": "create_task", "enabled": True,
        "config": {},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Srl", "created_at": _days_ago(200)}]
    appointments = [{
        "id": "a-1", "user_id": "user-1", "client_id": "c-1",
        "status": "completato", "start": _days_ago(5),
    }]
    engine = build_engine(automations=automations, clients=clients, appointments=appointments)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


def test_create_task_usa_le_09_del_mattino_in_ora_italiana_di_default(monkeypatch):
    """Il caso che ha motivato il fix: prima veniva usato 'adesso in UTC +
    24 ore', che produceva un task all'orario esatto in cui capitava di
    girare il ciclo (es. le 21:30 di notte) invece di un orario lavorativo.
    Di default deve finire domani alle 09:00 ora italiana."""
    from core.utils import now_local, local_wallclock_to_utc_iso
    from datetime import timedelta as td

    automations = [{
        "id": "auto-2", "user_id": "user-1", "name": "Cliente non visitato",
        "trigger": "no_visit_30d", "action": "create_task", "enabled": True,
        "config": {},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Srl", "created_at": _days_ago(200)}]
    engine = build_engine(automations=automations, clients=clients)

    created = []

    class FakeAppointmentService:
        async def create_appointment(self, user, payload):
            created.append(payload)
            return {"id": "new-appt"}

    import services.appointment_service as appt_mod
    monkeypatch.setattr(appt_mod, "appointment_service", FakeAppointmentService())

    run(engine.run_cycle())

    expected_date = (now_local() + td(days=1)).date().isoformat()
    expected_start = local_wallclock_to_utc_iso(f"{expected_date}T09:00:00")
    assert created[0].start == expected_start


def test_create_task_rispetta_task_time_e_task_delay_days_configurati(monkeypatch):
    from core.utils import now_local, local_wallclock_to_utc_iso
    from datetime import timedelta as td

    automations = [{
        "id": "auto-2", "user_id": "user-1", "name": "Cliente non visitato",
        "trigger": "no_visit_30d", "action": "create_task", "enabled": True,
        "config": {"task_time": "14:30", "task_delay_days": 3},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Srl", "created_at": _days_ago(200)}]
    engine = build_engine(automations=automations, clients=clients)

    created = []

    class FakeAppointmentService:
        async def create_appointment(self, user, payload):
            created.append(payload)
            return {"id": "new-appt"}

    import services.appointment_service as appt_mod
    monkeypatch.setattr(appt_mod, "appointment_service", FakeAppointmentService())

    run(engine.run_cycle())

    expected_date = (now_local() + td(days=3)).date().isoformat()
    expected_start = local_wallclock_to_utc_iso(f"{expected_date}T14:30:00")
    assert created[0].start == expected_start


def test_create_task_con_task_time_malformato_ricade_sul_default(monkeypatch):
    """Una config['task_time'] scritta male non deve mai far fallire la
    creazione del task: ricade sull'orario di default (09:00)."""
    from core.utils import now_local, local_wallclock_to_utc_iso
    from datetime import timedelta as td

    automations = [{
        "id": "auto-2", "user_id": "user-1", "name": "Cliente non visitato",
        "trigger": "no_visit_30d", "action": "create_task", "enabled": True,
        "config": {"task_time": "non-un-orario"},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Srl", "created_at": _days_ago(200)}]
    engine = build_engine(automations=automations, clients=clients)

    created = []

    class FakeAppointmentService:
        async def create_appointment(self, user, payload):
            created.append(payload)
            return {"id": "new-appt"}

    import services.appointment_service as appt_mod
    monkeypatch.setattr(appt_mod, "appointment_service", FakeAppointmentService())

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    expected_date = (now_local() + td(days=1)).date().isoformat()
    expected_start = local_wallclock_to_utc_iso(f"{expected_date}T09:00:00")
    assert created[0].start == expected_start


# ---------- lead_inactive + send_email ----------

def test_lead_inattivo_invia_email_al_lead():
    automations = [{
        "id": "auto-3", "user_id": "user-1", "name": "Lead inattivo",
        "trigger": "lead_inactive", "action": "send_email", "enabled": True,
        "config": {"days": 7},
    }]
    leads = [{
        "id": "l-1", "user_id": "user-1", "company_name": "Bianchi Spa",
        "email": "bianchi@example.com", "status": "contattato", "created_at": _days_ago(10),
    }]
    engine = build_engine(automations=automations, leads=leads)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    assert engine._sent_emails[0]["to"] == "bianchi@example.com"


def test_lead_vinto_non_viene_considerato_inattivo():
    automations = [{
        "id": "auto-3", "user_id": "user-1", "name": "Lead inattivo",
        "trigger": "lead_inactive", "action": "send_email", "enabled": True,
        "config": {"days": 7},
    }]
    leads = [{
        "id": "l-1", "user_id": "user-1", "company_name": "Bianchi Spa",
        "email": "bianchi@example.com", "status": "vinto", "created_at": _days_ago(30),
    }]
    engine = build_engine(automations=automations, leads=leads)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


def test_lead_vecchio_ma_contattato_di_recente_non_e_inattivo():
    """Lo scenario che ha motivato il fix: un lead creato 60 giorni fa ma
    contattato ieri non deve essere considerato inattivo — prima veniva
    usato solo created_at, che lo avrebbe segnalato erroneamente."""
    automations = [{
        "id": "auto-3", "user_id": "user-1", "name": "Lead inattivo",
        "trigger": "lead_inactive", "action": "send_email", "enabled": True,
        "config": {"days": 7},
    }]
    leads = [{
        "id": "l-1", "user_id": "user-1", "company_name": "Bianchi Spa",
        "email": "bianchi@example.com", "status": "contattato",
        "created_at": _days_ago(60), "last_interaction_at": _days_ago(1),
    }]
    engine = build_engine(automations=automations, leads=leads)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


def test_lead_senza_last_interaction_at_ricade_su_created_at():
    """Retrocompatibilità: un lead creato prima dell'introduzione del
    campo last_interaction_at (quindi privo di quel campo) continua a
    usare created_at come prima, invece di non essere mai valutato."""
    automations = [{
        "id": "auto-3", "user_id": "user-1", "name": "Lead inattivo",
        "trigger": "lead_inactive", "action": "send_email", "enabled": True,
        "config": {"days": 7},
    }]
    leads = [{
        "id": "l-1", "user_id": "user-1", "company_name": "Bianchi Spa",
        "email": "bianchi@example.com", "status": "contattato", "created_at": _days_ago(10),
    }]
    engine = build_engine(automations=automations, leads=leads)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1


# ---------- Retry ed errori persistenti ----------

def test_errore_persistente_smette_di_essere_ritentato_dopo_max_tentativi():
    automations = [{
        "id": "auto-4", "user_id": "user-1", "name": "Lead inattivo (email rotta)",
        "trigger": "lead_inactive", "action": "send_email", "enabled": True,
        "config": {"days": 7},
    }]
    leads = [{
        "id": "l-1", "user_id": "user-1", "company_name": "Bianchi Spa",
        "email": "", "status": "nuovo", "created_at": _days_ago(10),
    }]

    async def failing_send_email(to, subject, html):
        raise AssertionError("non dovrebbe mai essere chiamato: nessuna email disponibile")

    engine = build_engine(automations=automations, leads=leads, send_email_fn=failing_send_email)
    # Nessuna email sul lead e nessuna sull'utente -> _action_send_email solleva
    # RuntimeError("Nessun indirizzo email disponibile...") prima di chiamare send_email_fn.
    engine.user_repo.users["user-1"]["email"] = ""

    for _ in range(AUTOMATION_MAX_ATTEMPTS):
        run(engine.run_cycle())

    run_doc = engine.run_repo.docs[("auto-4", "l-1")]
    assert run_doc["attempts"] == AUTOMATION_MAX_ATTEMPTS
    assert run_doc["status"] == "failed_permanent"

    # Un ciclo ulteriore non deve ritentare più (should_run == False).
    summary = run(engine.run_cycle())
    assert summary["executed"] == 0
    assert summary["errors"] == 0
    assert summary["skipped"] == 1
    assert engine.run_repo.docs[("auto-4", "l-1")]["attempts"] == AUTOMATION_MAX_ATTEMPTS


def test_errore_transitorio_viene_ritentato_e_puo_riuscire():
    automations = [{
        "id": "auto-5", "user_id": "user-1", "name": "Lead inattivo",
        "trigger": "lead_inactive", "action": "send_email", "enabled": True,
        "config": {"days": 7},
    }]
    leads = [{
        "id": "l-1", "user_id": "user-1", "company_name": "Bianchi Spa",
        "email": "bianchi@example.com", "status": "nuovo", "created_at": _days_ago(10),
    }]

    calls = {"n": 0}

    async def flaky_send_email(to, subject, html):
        calls["n"] += 1
        if calls["n"] == 1:
            return False  # simula un invio fallito (send_email ritorna False)
        return True

    engine = build_engine(automations=automations, leads=leads, send_email_fn=flaky_send_email)

    first = run(engine.run_cycle())
    second = run(engine.run_cycle())

    assert first["errors"] == 1
    assert second["executed"] == 1
    assert engine.run_repo.docs[("auto-5", "l-1")]["status"] == "ok"


# ---------- Account demo: nessun invio/scrittura reale ----------

def test_utente_demo_non_riceve_email_ma_notifica_in_app_si():
    automations = [{
        "id": "auto-6", "user_id": "user-demo", "name": "Promemoria scadenza",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 3},
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-demo", "client_id": "c-1", "title": "Offerta demo",
        "status": "inviata", "expires_at": _days_from_now(2),
    }]
    users = [{"id": "user-demo", "email": "demo@example.com", "is_demo": True}]
    engine = build_engine(automations=automations, offers=offers, users=users)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    assert len(engine.notification_repo.docs) == 1  # notifica in-app comunque creata
    assert len(engine._sent_emails) == 0  # ma nessuna email reale inviata


def test_ultima_esecuzione_registra_conteggi_su_automazione():
    """L'automazione stessa deve riportare quante azioni sono state
    eseguite/saltate/fallite nell'ultimo ciclo — usato dall'interfaccia per
    mostrare 'Ultima esecuzione: ... Risultato: N azioni eseguite'."""
    automations = [{
        "id": "auto-7", "user_id": "user-1", "name": "Promemoria scadenza",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 3},
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-1", "client_id": "c-1", "title": "Offerta A",
        "status": "inviata", "expires_at": _days_from_now(2),
    }]
    engine = build_engine(automations=automations, offers=offers)

    run(engine.run_cycle())

    updated = next(a for a in engine.automation_repo.docs if a["id"] == "auto-7")
    assert updated["last_run_executed"] == 1
    assert updated["last_run_skipped"] == 0
    assert updated["last_run_errors"] == 0
    assert updated["last_run_status"] == "ok"
    assert updated["last_run_at"] is not None


# ---------- Oggetto/contenuto email personalizzati ----------

def test_send_email_usa_oggetto_e_contenuto_personalizzati():
    automations = [{
        "id": "auto-8", "user_id": "user-1", "name": "Lead inattivo",
        "trigger": "lead_inactive", "action": "send_email", "enabled": True,
        "config": {
            "days": 7,
            "email_subject": "Ciao {nome}, ci sei ancora?",
            "email_message": "Notiamo che {nome} ({citta}) non risponde da un po'.",
        },
    }]
    leads = [{
        "id": "l-1", "user_id": "user-1", "company_name": "Bianchi Spa",
        "email": "bianchi@example.com", "city": "Ancona", "status": "nuovo", "created_at": _days_ago(10),
    }]
    engine = build_engine(automations=automations, leads=leads)

    run(engine.run_cycle())

    assert len(engine._sent_emails) == 1
    assert engine._sent_emails[0]["subject"] == "Ciao Bianchi Spa, ci sei ancora?"
    assert "Bianchi Spa (Ancona)" in engine._sent_emails[0]["html"]


def test_send_reminder_usa_oggetto_e_contenuto_personalizzati():
    automations = [{
        "id": "auto-9", "user_id": "user-1", "name": "Promemoria scadenza",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {
            "days_before": 3,
            "email_subject": "Offerta {nome} in scadenza",
            "email_message": "L'offerta {nome} scade il {scadenza}, contatta il cliente.",
        },
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-1", "client_id": "c-1", "title": "Fornitura Uffici",
        "status": "inviata", "expires_at": _days_from_now(2),
    }]
    engine = build_engine(automations=automations, offers=offers)

    run(engine.run_cycle())

    assert len(engine._sent_emails) == 1
    assert "🔔 SALESFLY — Offerta Fornitura Uffici in scadenza" == engine._sent_emails[0]["subject"]
    assert "Fornitura Uffici" in engine._sent_emails[0]["html"]
    assert len(engine.notification_repo.docs) == 1
    assert "Fornitura Uffici" in engine.notification_repo.docs[0]["message"]


def test_placeholder_sconosciuto_non_fa_fallire_linvio():
    """Un typo nel placeholder (es. '{nom}' invece di '{nome}') non deve
    mai far fallire l'invio: viene lasciato letterale nel testo."""
    automations = [{
        "id": "auto-10", "user_id": "user-1", "name": "Lead inattivo",
        "trigger": "lead_inactive", "action": "send_email", "enabled": True,
        "config": {"days": 7, "email_message": "Ciao {nom}, tutto ok?"},
    }]
    leads = [{
        "id": "l-1", "user_id": "user-1", "company_name": "Bianchi Spa",
        "email": "bianchi@example.com", "status": "nuovo", "created_at": _days_ago(10),
    }]
    engine = build_engine(automations=automations, leads=leads)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    assert "{nom}" in engine._sent_emails[0]["html"]  # lasciato letterale, non un crash


# ---------- Orario di esecuzione per regola (config['run_at']) ----------

def test_regola_senza_run_at_viene_valutata_sempre():
    automations = [{
        "id": "auto-11", "user_id": "user-1", "name": "Promemoria scadenza",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 3},
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-1", "client_id": "c-1", "title": "Offerta A",
        "status": "inviata", "expires_at": _days_from_now(2),
    }]
    engine = build_engine(automations=automations, offers=offers)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1


def test_regola_fuori_dalla_finestra_oraria_non_viene_valutata(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime

    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 7, 26, 8, 0))

    automations = [{
        "id": "auto-12", "user_id": "user-1", "name": "Promemoria scadenza",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 3, "run_at": "18:00"},
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-1", "client_id": "c-1", "title": "Offerta A",
        "status": "inviata", "expires_at": _days_from_now(2),
    }]
    engine = build_engine(automations=automations, offers=offers)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0
    assert engine._sent_emails == []
    # Fuori dalla finestra: la regola non è stata valutata affatto, quindi
    # last_run_at non deve essere stato toccato.
    updated = next(a for a in engine.automation_repo.docs if a["id"] == "auto-12")
    assert updated.get("last_run_at") is None


def test_regola_dentro_la_finestra_oraria_viene_valutata(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime

    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 7, 26, 18, 3))

    automations = [{
        "id": "auto-13", "user_id": "user-1", "name": "Promemoria scadenza",
        "trigger": "offer_expiring", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 3, "run_at": "18:00"},
    }]
    offers = [{
        "id": "offer-1", "user_id": "user-1", "client_id": "c-1", "title": "Offerta A",
        "status": "inviata", "expires_at": _days_from_now(2),
    }]
    engine = build_engine(automations=automations, offers=offers)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    updated = next(a for a in engine.automation_repo.docs if a["id"] == "auto-13")
    assert updated["last_run_at"] is not None


# ---------- no_order_days ----------

def test_cliente_senza_ordini_da_90_giorni_genera_promemoria():
    automations = [{
        "id": "auto-20", "user_id": "user-1", "name": "Cliente senza ordini",
        "trigger": "no_order_days", "action": "send_reminder", "enabled": True,
        "config": {"days": 90},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Spa", "created_at": _days_ago(400)}]
    orders = [{"id": "o-1", "user_id": "user-1", "client_id": "c-1", "created_at": _days_ago(120)}]
    engine = build_engine(automations=automations, clients=clients, orders=orders)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    assert "Rossi Spa" in engine.notification_repo.docs[0]["message"]


def test_cliente_con_ordine_recente_non_genera_nulla():
    automations = [{
        "id": "auto-20", "user_id": "user-1", "name": "Cliente senza ordini",
        "trigger": "no_order_days", "action": "send_reminder", "enabled": True,
        "config": {"days": 90},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Spa", "created_at": _days_ago(400)}]
    orders = [{"id": "o-1", "user_id": "user-1", "client_id": "c-1", "created_at": _days_ago(10)}]
    engine = build_engine(automations=automations, clients=clients, orders=orders)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


def test_cliente_senza_alcun_ordine_usa_created_at_come_riferimento():
    automations = [{
        "id": "auto-20", "user_id": "user-1", "name": "Cliente senza ordini",
        "trigger": "no_order_days", "action": "send_reminder", "enabled": True,
        "config": {"days": 90},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Spa", "created_at": _days_ago(200)}]
    engine = build_engine(automations=automations, clients=clients)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1


def test_cliente_appena_creato_senza_ordini_non_e_ancora_segnalato():
    automations = [{
        "id": "auto-20", "user_id": "user-1", "name": "Cliente senza ordini",
        "trigger": "no_order_days", "action": "send_reminder", "enabled": True,
        "config": {"days": 90},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Spa", "created_at": _days_ago(5)}]
    engine = build_engine(automations=automations, clients=clients)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


# ---------- client_created ----------

def test_nuovo_cliente_genera_follow_up(monkeypatch):
    automations = [{
        "id": "auto-21", "user_id": "user-1", "name": "Nuovo cliente",
        "trigger": "client_created", "action": "create_task", "enabled": True,
        "config": {"days": 2},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Bianchi Srl", "created_at": _days_ago(1)}]
    engine = build_engine(automations=automations, clients=clients)

    created = []

    class FakeAppointmentService:
        async def create_appointment(self, user, payload):
            created.append(payload)
            return {"id": "new-appt"}

    import services.appointment_service as appt_mod
    monkeypatch.setattr(appt_mod, "appointment_service", FakeAppointmentService())

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    assert created[0].client_id == "c-1"


def test_cliente_creato_troppo_tempo_fa_non_e_piu_nuovo():
    automations = [{
        "id": "auto-21", "user_id": "user-1", "name": "Nuovo cliente",
        "trigger": "client_created", "action": "send_reminder", "enabled": True,
        "config": {"days": 2},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Bianchi Srl", "created_at": _days_ago(10)}]
    engine = build_engine(automations=automations, clients=clients)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


def test_nuovo_cliente_genera_follow_up_una_sola_volta():
    """Anche restando nella finestra 'days' della config, lo stesso cliente
    non deve generare un secondo follow-up in un ciclo successivo (dedup su
    automation_runs, nessun cooldown_days impostato -> una sola volta mai)."""
    automations = [{
        "id": "auto-21", "user_id": "user-1", "name": "Nuovo cliente",
        "trigger": "client_created", "action": "send_reminder", "enabled": True,
        "config": {"days": 2},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Bianchi Srl", "created_at": _days_ago(1)}]
    engine = build_engine(automations=automations, clients=clients)

    first = run(engine.run_cycle())
    second = run(engine.run_cycle())

    assert first["executed"] == 1
    assert second["executed"] == 0
    assert second["skipped"] == 1


# ---------- client_birthday ----------

def test_compleanno_oggi_genera_promemoria(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime
    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 15, 9, 0))

    automations = [{
        "id": "auto-22", "user_id": "user-1", "name": "Compleanno cliente",
        "trigger": "client_birthday", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 0},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Verdi Spa", "birthday": "1980-03-15"}]
    engine = build_engine(automations=automations, clients=clients)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    assert engine.run_repo.docs[("auto-22", "c-1:2026")]["status"] == "ok"


def test_compleanno_non_oggi_non_genera_nulla(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime
    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 15, 9, 0))

    automations = [{
        "id": "auto-22", "user_id": "user-1", "name": "Compleanno cliente",
        "trigger": "client_birthday", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 0},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Verdi Spa", "birthday": "1980-06-20"}]
    engine = build_engine(automations=automations, clients=clients)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


def test_compleanno_si_ripete_lanno_successivo(monkeypatch):
    """Il target_id include l'anno apposta: lo stesso cliente deve generare
    di nuovo un promemoria l'anno dopo, senza bisogno di cooldown_days."""
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime

    automations = [{
        "id": "auto-22", "user_id": "user-1", "name": "Compleanno cliente",
        "trigger": "client_birthday", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 0},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Verdi Spa", "birthday": "1980-03-15"}]
    engine = build_engine(automations=automations, clients=clients)

    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 15, 9, 0))
    first = run(engine.run_cycle())

    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2027, 3, 15, 9, 0))
    second = run(engine.run_cycle())

    assert first["executed"] == 1
    assert second["executed"] == 1  # non "skipped": è un anno nuovo


def test_compleanno_con_giorni_di_anticipo(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime
    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 12, 9, 0))

    automations = [{
        "id": "auto-22", "user_id": "user-1", "name": "Compleanno cliente",
        "trigger": "client_birthday", "action": "send_reminder", "enabled": True,
        "config": {"days_before": 5},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Verdi Spa", "birthday": "1980-03-15"}]
    engine = build_engine(automations=automations, clients=clients)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1


# ---------- tomorrow_appointments (digest) ----------

def test_digest_domani_conta_le_visite_di_domani(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime
    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 15, 18, 0))

    automations = [{
        "id": "auto-23", "user_id": "user-1", "name": "Domani hai visite",
        "trigger": "tomorrow_appointments", "action": "send_reminder", "enabled": True,
        "config": {"run_at": "18:00"},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Spa"}]
    appointments = [
        {"id": "a-1", "user_id": "user-1", "client_id": "c-1", "status": "pianificato", "start": "2026-03-16T09:00:00+01:00"},
        {"id": "a-2", "user_id": "user-1", "client_id": "c-1", "status": "pianificato", "start": "2026-03-16T11:00:00+01:00"},
        {"id": "a-3", "user_id": "user-1", "client_id": "c-1", "status": "pianificato", "start": "2026-03-17T09:00:00+01:00"},  # dopodomani, non conta
    ]
    engine = build_engine(automations=automations, clients=clients, appointments=appointments)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    assert "2 visite" in engine.notification_repo.docs[0]["message"]


def test_digest_domani_nessuna_visita_non_genera_nulla(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime
    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 15, 18, 0))

    automations = [{
        "id": "auto-23", "user_id": "user-1", "name": "Domani hai visite",
        "trigger": "tomorrow_appointments", "action": "send_reminder", "enabled": True,
        "config": {"run_at": "18:00"},
    }]
    engine = build_engine(automations=automations)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


def test_digest_domani_una_sola_volta_al_giorno(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime
    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 15, 18, 0))

    automations = [{
        "id": "auto-23", "user_id": "user-1", "name": "Domani hai visite",
        "trigger": "tomorrow_appointments", "action": "send_reminder", "enabled": True,
        "config": {"run_at": "18:00"},
    }]
    clients = [{"id": "c-1", "user_id": "user-1", "company_name": "Rossi Spa"}]
    appointments = [
        {"id": "a-1", "user_id": "user-1", "client_id": "c-1", "status": "pianificato", "start": "2026-03-16T09:00:00+01:00"},
    ]
    engine = build_engine(automations=automations, clients=clients, appointments=appointments)

    first = run(engine.run_cycle())
    second = run(engine.run_cycle())

    assert first["executed"] == 1
    assert second["executed"] == 0
    assert second["skipped"] == 1


# ---------- commissions_below_target_mid_month (digest) ----------

def test_provvigioni_sotto_obiettivo_a_meta_mese(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime
    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 15, 9, 0))

    automations = [{
        "id": "auto-24", "user_id": "user-1", "name": "Provvigioni sotto obiettivo",
        "trigger": "commissions_below_target_mid_month", "action": "send_reminder", "enabled": True,
        "config": {"check_day": 15, "threshold_pct": 50},
    }]
    users = [{"id": "user-1", "email": "agente@example.com", "goal_commissions": 2000}]
    commissions = [{"id": "com-1", "user_id": "user-1", "amount": 400, "created_at": "2026-03-05T10:00:00Z"}]
    engine = build_engine(automations=automations, users=users, commissions=commissions)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 1
    msg = engine.notification_repo.docs[0]["message"]
    assert "20%" in msg


def test_provvigioni_sopra_soglia_non_genera_nulla(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime
    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 15, 9, 0))

    automations = [{
        "id": "auto-24", "user_id": "user-1", "name": "Provvigioni sotto obiettivo",
        "trigger": "commissions_below_target_mid_month", "action": "send_reminder", "enabled": True,
        "config": {"check_day": 15, "threshold_pct": 50},
    }]
    users = [{"id": "user-1", "email": "agente@example.com", "goal_commissions": 2000}]
    commissions = [{"id": "com-1", "user_id": "user-1", "amount": 1200, "created_at": "2026-03-05T10:00:00Z"}]
    engine = build_engine(automations=automations, users=users, commissions=commissions)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


def test_provvigioni_non_valutato_fuori_dal_giorno_di_controllo(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime
    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 10, 9, 0))

    automations = [{
        "id": "auto-24", "user_id": "user-1", "name": "Provvigioni sotto obiettivo",
        "trigger": "commissions_below_target_mid_month", "action": "send_reminder", "enabled": True,
        "config": {"check_day": 15, "threshold_pct": 50},
    }]
    users = [{"id": "user-1", "email": "agente@example.com", "goal_commissions": 2000}]
    commissions = [{"id": "com-1", "user_id": "user-1", "amount": 100, "created_at": "2026-03-05T10:00:00Z"}]
    engine = build_engine(automations=automations, users=users, commissions=commissions)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


def test_provvigioni_senza_obiettivo_impostato_non_genera_nulla(monkeypatch):
    import services.automation_engine as automation_engine_mod
    from datetime import datetime as real_datetime
    monkeypatch.setattr(automation_engine_mod, "now_local", lambda: real_datetime(2026, 3, 15, 9, 0))

    automations = [{
        "id": "auto-24", "user_id": "user-1", "name": "Provvigioni sotto obiettivo",
        "trigger": "commissions_below_target_mid_month", "action": "send_reminder", "enabled": True,
        "config": {"check_day": 15, "threshold_pct": 50},
    }]
    users = [{"id": "user-1", "email": "agente@example.com"}]  # nessun goal_commissions
    engine = build_engine(automations=automations, users=users)

    summary = run(engine.run_cycle())

    assert summary["executed"] == 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
