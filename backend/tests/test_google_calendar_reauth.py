"""
Verifica il comportamento aggiunto a google_calendar_service quando Google
rifiuta il refresh token (tipicamente perche' l'app OAuth e' ancora in stato
"Test" su Google Cloud, che fa scadere i token dopo ~7 giorni, o perche'
l'utente ha revocato l'accesso): il sistema deve accorgersene, segnare la
connessione come 'needs_reauth', e avvisare l'utente (email + notifica
in-app) UNA volta, rispettando un cooldown — non ad ogni ciclo di sync.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_google_calendar_reauth.py -v
"""
import sys
import time
import asyncio
from datetime import datetime, timedelta, timezone

import requests
import pytest

sys.path.insert(0, ".")

import services.google_calendar_service as gcal_mod
from services.google_calendar_service import GoogleCalendarService
from core.crypto import encrypt_str
from core.config import GOOGLE_REAUTH_NOTIFY_COOLDOWN_HOURS


def run(coro):
    return asyncio.run(coro)


def _iso_ago(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


class FakeResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            err = requests.HTTPError(f"{self.status_code} error")
            err.response = self
            raise err

    def json(self):
        return self._json


class FakeGcalRepo:
    def __init__(self, conn=None):
        self.conn = dict(conn) if conn else None

    async def find_by_user(self, user_id):
        return dict(self.conn) if self.conn and self.conn["user_id"] == user_id else None

    async def upsert(self, user_id, data):
        if self.conn is None:
            self.conn = {"user_id": user_id}
        self.conn.update(data)


class FakeNotificationRepo:
    def __init__(self):
        self.docs = []

    async def insert(self, doc):
        self.docs.append(doc)
        return doc


class FakeUserRepo:
    def __init__(self, users):
        self.users = {u["id"]: u for u in users}

    async def find_by_id(self, uid):
        return dict(self.users[uid]) if uid in self.users else None


def build_service(conn, send_email_fn=None):
    sent = []

    async def default_send_email(to, subject, html):
        sent.append({"to": to, "subject": subject, "html": html})
        return True

    repo = FakeGcalRepo(conn)
    service = GoogleCalendarService(
        repo=repo,
        notification_repo=FakeNotificationRepo(),
        user_repo=FakeUserRepo([{"id": "user-1", "email": "agente@example.com"}]),
        send_email_fn=send_email_fn or default_send_email,
    )
    service._sent_emails = sent
    return service


def _base_conn():
    return {
        "user_id": "user-1",
        "refresh_token_enc": encrypt_str("refresh-token-fittizio"),
        "access_token": "expired",
        "access_token_expiry": 0,  # forza il refresh
    }


def test_refresh_400_marca_needs_reauth_e_notifica(monkeypatch):
    monkeypatch.setattr(gcal_mod.requests, "post", lambda *a, **k: FakeResponse(400))
    service = build_service(_base_conn())

    token = run(service._valid_access_token(service.repo.conn))

    assert token is None
    assert service.repo.conn["needs_reauth"] is True
    assert len(service.notification_repo.docs) == 1
    assert service.notification_repo.docs[0]["target_type"] == "google_calendar"
    assert len(service._sent_emails) == 1
    assert service._sent_emails[0]["to"] == "agente@example.com"


def test_refresh_400_ripetuto_entro_cooldown_non_rispedisce_email(monkeypatch):
    monkeypatch.setattr(gcal_mod.requests, "post", lambda *a, **k: FakeResponse(400))
    service = build_service(_base_conn())

    run(service._valid_access_token(service.repo.conn))
    # Simula un secondo ciclo di sync (5 minuti dopo): la connessione in DB
    # ora ha gia' needs_reauth=True e un reauth_notified_at recente.
    run(service._valid_access_token(service.repo.conn))

    assert len(service._sent_emails) == 1  # non due
    assert len(service.notification_repo.docs) == 1


def test_refresh_400_dopo_cooldown_scaduto_rispedisce_email(monkeypatch):
    monkeypatch.setattr(gcal_mod.requests, "post", lambda *a, **k: FakeResponse(400))
    conn = _base_conn()
    conn["needs_reauth"] = True
    conn["reauth_notified_at"] = _iso_ago(GOOGLE_REAUTH_NOTIFY_COOLDOWN_HOURS + 1)
    service = build_service(conn)

    run(service._valid_access_token(service.repo.conn))

    assert len(service._sent_emails) == 1


def test_refresh_riuscito_dopo_fallimento_resetta_needs_reauth(monkeypatch):
    conn = _base_conn()
    conn["needs_reauth"] = True
    conn["reauth_notified_at"] = _iso_ago(1)
    service = build_service(conn)

    monkeypatch.setattr(
        gcal_mod.requests, "post",
        lambda *a, **k: FakeResponse(200, {"access_token": "nuovo-token", "expires_in": 3600}),
    )

    token = run(service._valid_access_token(service.repo.conn))

    assert token == "nuovo-token"
    assert service.repo.conn["needs_reauth"] is False
    assert service.repo.conn["reauth_notified_at"] is None


def test_errore_di_rete_5xx_non_marca_needs_reauth(monkeypatch):
    """Un 5xx (problema temporaneo lato Google, non un token rifiutato) non
    deve far scattare l'avviso di riconnessione: si ritenta al prossimo
    ciclo senza allarmare l'utente per un errore transitorio."""
    monkeypatch.setattr(gcal_mod.requests, "post", lambda *a, **k: FakeResponse(503))
    service = build_service(_base_conn())

    token = run(service._valid_access_token(service.repo.conn))

    assert token is None
    assert service.repo.conn.get("needs_reauth") is not True
    assert service.notification_repo.docs == []
    assert service._sent_emails == []


def test_get_status_espone_needs_reauth():
    conn = _base_conn()
    conn["needs_reauth"] = True
    conn["google_email"] = "agente@gmail.com"
    service = build_service(conn)

    status = run(service.get_status("user-1"))

    assert status == {"connected": True, "google_email": "agente@gmail.com", "needs_reauth": True}


# ---------- push_create/update/delete: nessuna sincronizzazione reale per il demo ----------

class FakeApptRepo:
    def __init__(self):
        self.updates = []

    async def update(self, aid, user_id, data):
        self.updates.append((aid, user_id, data))


def _connected_valid_conn():
    # access_token già valido (nessun refresh necessario): isola il test sul
    # comportamento di push_create/update/delete, non su _valid_access_token.
    return {
        "user_id": "user-1", "calendar_id": "primary",
        "access_token": "token-valido", "access_token_expiry": time.time() + 3600,
        "refresh_token_enc": encrypt_str("refresh-token-fittizio"),
    }


def build_push_service(conn, user, appt_repo=None):
    repo = FakeGcalRepo(conn)
    return GoogleCalendarService(
        repo=repo, appt_repo=appt_repo or FakeApptRepo(),
        notification_repo=FakeNotificationRepo(),
        user_repo=FakeUserRepo([user]),
        send_email_fn=lambda *a, **k: None,
    )


def _fail_if_called(*a, **k):
    raise AssertionError("nessuna chiamata reale a Google doveva partire per l'account demo")


def test_push_create_non_chiama_google_per_account_demo(monkeypatch):
    monkeypatch.setattr(gcal_mod.requests, "post", _fail_if_called)
    service = build_push_service(_connected_valid_conn(), {"id": "user-1", "is_demo": True})

    run(service.push_create("user-1", {"id": "appt-1", "title": "Visita", "start": "2026-01-01T09:00:00"}))
    # Nessuna eccezione = nessuna chiamata HTTP tentata (il fake alza AssertionError se chiamato).


def test_push_update_non_chiama_google_per_account_demo(monkeypatch):
    monkeypatch.setattr(gcal_mod.requests, "patch", _fail_if_called)
    monkeypatch.setattr(gcal_mod.requests, "post", _fail_if_called)
    service = build_push_service(_connected_valid_conn(), {"id": "user-1", "is_demo": True})

    run(service.push_update("user-1", {"id": "appt-1", "title": "Visita", "start": "2026-01-01T09:00:00", "google_event_id": "evt-1"}))


def test_push_delete_non_chiama_google_per_account_demo(monkeypatch):
    monkeypatch.setattr(gcal_mod.requests, "delete", _fail_if_called)
    service = build_push_service(_connected_valid_conn(), {"id": "user-1", "is_demo": True})

    run(service.push_delete("user-1", "evt-1"))


def test_push_create_funziona_normalmente_per_utente_non_demo(monkeypatch):
    monkeypatch.setattr(
        gcal_mod.requests, "post",
        lambda *a, **k: FakeResponse(200, {"id": "evt-nuovo"}),
    )
    appt_repo = FakeApptRepo()
    service = build_push_service(_connected_valid_conn(), {"id": "user-1", "is_demo": False}, appt_repo=appt_repo)

    run(service.push_create("user-1", {"id": "appt-1", "title": "Visita", "start": "2026-01-01T09:00:00"}))

    assert appt_repo.updates == [("appt-1", "user-1", {"google_event_id": "evt-nuovo"})]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
