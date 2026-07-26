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

    def _key(self, automation_id, target_id):
        return (automation_id, target_id)

    async def find_one(self, automation_id, target_id):
        d = self.docs.get(self._key(automation_id, target_id))
        return dict(d) if d else None

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
                  appointments=None, users=None, send_email_fn=None):
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
