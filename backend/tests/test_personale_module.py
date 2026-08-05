"""
Verifica il modulo "Personale" (services/employee_service.py +
services/leave_request_service.py): CACI SRL gestisce i propri dipendenti
e le loro richieste di ferie/permessi/malattia, inviate dal dipendente
tramite un link personale senza bisogno di un account SalesFly.

Copre:
- create_employee genera un request_token univoco, usato dal form
  pubblico (routers/leave_requests.py POST "") per risalire a dipendente
  + azienda senza autenticazione.
- submit rifiuta un token sconosciuto/disattivato e un intervallo di
  date invertito; denormalizza employee_name sulla richiesta (resta
  leggibile anche se il dipendente viene poi eliminato).
- decide blocca una seconda decisione sulla stessa richiesta (non può
  passare da "approvata" a "rifiutata" o viceversa).
- calendar restituisce solo le richieste APPROVATE che si sovrappongono
  al mese richiesto.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_personale_module.py -v
"""
import sys
import asyncio

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, ".")

from core.exceptions import NotFoundError, ValidationAppError
from models.employee import EmployeeIn
from models.leave_request import LeaveRequestIn
from services.employee_service import EmployeeService
import services.leave_request_service as leave_request_mod
from services.leave_request_service import LeaveRequestService


def run(coro):
    return asyncio.run(coro)


USER = {"id": "user-1", "email": "manager@example.com"}


class FakeEmployeeRepo:
    def __init__(self):
        self.docs = {}

    async def find_many(self, user_id):
        return [d for d in self.docs.values() if d["user_id"] == user_id]

    async def find_one(self, eid, user_id):
        d = self.docs.get(eid)
        return d if d and d["user_id"] == user_id else None

    async def find_by_token_hash(self, token_hash):
        for d in self.docs.values():
            if d["request_token_hash"] == token_hash:
                return d
        return None

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, eid, user_id, data):
        d = self.docs.get(eid)
        if not d or d["user_id"] != user_id:
            return False
        d.update(data)
        return True

    async def touch_last_used(self, eid, ts):
        d = self.docs.get(eid)
        if d:
            d["last_used_at"] = ts

    async def delete(self, eid, user_id):
        d = self.docs.get(eid)
        if d and d["user_id"] == user_id:
            del self.docs[eid]


class FakeLeaveRequestRepo:
    def __init__(self):
        self.docs = {}

    async def find_many(self, user_id, status=None):
        rows = [d for d in self.docs.values() if d["user_id"] == user_id]
        if status:
            rows = [d for d in rows if d["status"] == status]
        return rows

    async def find_one(self, rid, user_id):
        d = self.docs.get(rid)
        return d if d and d["user_id"] == user_id else None

    async def find_overlapping(self, user_id, date_from, date_to, status="approvata"):
        return [
            d for d in self.docs.values()
            if d["user_id"] == user_id and d["status"] == status
            and d["date_from"] <= date_to and d["date_to"] >= date_from
        ]

    async def find_by_employee(self, employee_id):
        return [d for d in self.docs.values() if d["employee_id"] == employee_id]

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, rid, user_id, data):
        d = self.docs.get(rid)
        if not d or d["user_id"] != user_id:
            return False
        d.update(data)
        return True

    async def decide(self, rid, user_id, data):
        d = self.docs.get(rid)
        if not d or d["user_id"] != user_id or d["status"] != "in_attesa":
            return False
        d.update(data)
        return True


class FakeUserRepo:
    def __init__(self, users):
        self.users = users

    async def find_by_id(self, uid):
        return self.users.get(uid)


async def _noop_send_email(to, subject, html):
    return True


def build_employee_service():
    repo = FakeEmployeeRepo()
    return EmployeeService(repo=repo), repo


def build_leave_service(monkeypatch, employees_repo, manager=USER):
    monkeypatch.setattr(leave_request_mod, "send_email", _noop_send_email)
    monkeypatch.setattr(leave_request_mod, "check_and_record", lambda *a, **kw: _allow())
    repo = FakeLeaveRequestRepo()
    users = FakeUserRepo({manager["id"]: manager})
    service = LeaveRequestService(repo=repo, employees=employees_repo, users=users)
    return service, repo


async def _allow():
    return True


def make_employee(name="Mario Rossi", **overrides):
    payload = EmployeeIn(name=name, role=overrides.get("role", ""), email=overrides.get("email"))
    return payload


# ---------- employee_service ----------

def test_create_employee_genera_un_token_univoco():
    service, repo = build_employee_service()
    e1 = run(service.create_employee(USER, make_employee("Mario Rossi")))
    e2 = run(service.create_employee(USER, make_employee("Luca Bianchi")))
    assert e1["request_token"] != e2["request_token"]
    assert e1["user_id"] == USER["id"]


def test_get_by_token_rifiuta_token_sconosciuto():
    service, repo = build_employee_service()
    with pytest.raises(NotFoundError):
        run(service.get_by_token("token-inesistente"))


def test_get_by_token_rifiuta_dipendente_disattivato():
    service, repo = build_employee_service()
    employee = run(service.create_employee(USER, make_employee()))
    run(repo.update(employee["id"], USER["id"], {"active": False}))
    with pytest.raises(NotFoundError):
        run(service.get_by_token(employee["request_token"]))


def test_create_employee_non_salva_il_token_in_chiaro():
    service, repo = build_employee_service()
    employee = run(service.create_employee(USER, make_employee()))
    stored = repo.docs[employee["id"]]
    assert "request_token" not in stored
    assert stored["request_token_hash"]
    assert stored["request_token_hash"] != employee["request_token"]


def test_regenerate_token_invalida_il_precedente(monkeypatch):
    service, repo = build_employee_service()
    employee = run(service.create_employee(USER, make_employee()))
    old_token = employee["request_token"]

    new_token = run(service.regenerate_token(USER, employee["id"]))

    assert new_token != old_token
    with pytest.raises(NotFoundError):
        run(service.get_by_token(old_token))
    found = run(service.get_by_token(new_token))
    assert found["id"] == employee["id"]


def test_regenerate_token_rifiuta_dipendente_di_un_altro_utente():
    service, repo = build_employee_service()
    employee = run(service.create_employee(USER, make_employee()))
    altro = {"id": "user-2", "email": "altro@example.com"}
    with pytest.raises(NotFoundError):
        run(service.regenerate_token(altro, employee["id"]))


def test_set_active_disattiva_e_riattiva():
    service, repo = build_employee_service()
    employee = run(service.create_employee(USER, make_employee()))

    run(service.set_active(USER, employee["id"], False))
    with pytest.raises(NotFoundError):
        run(service.get_by_token(employee["request_token"]))

    run(service.set_active(USER, employee["id"], True))
    found = run(service.get_by_token(employee["request_token"]))
    assert found["id"] == employee["id"]


def test_get_by_token_aggiorna_last_used_at():
    service, repo = build_employee_service()
    employee = run(service.create_employee(USER, make_employee()))
    assert repo.docs[employee["id"]]["last_used_at"] is None

    run(service.get_by_token(employee["request_token"]))
    assert repo.docs[employee["id"]]["last_used_at"] is not None


# ---------- leave_request_service.submit ----------

def test_submit_rifiuta_token_sconosciuto(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    service, repo = build_leave_service(monkeypatch, emp_repo)
    payload = LeaveRequestIn(employee_token="non-esiste", type="ferie", date_from="2026-08-01", date_to="2026-08-05")
    with pytest.raises(NotFoundError):
        run(service.submit(payload))


def test_submit_rispetta_il_rate_limit_per_token(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))

    calls = []

    async def fake_check_and_record(kind, key, max_attempts, window_minutes):
        calls.append(kind)
        return kind != "leave_request_token"

    monkeypatch.setattr(leave_request_mod, "send_email", _noop_send_email)
    monkeypatch.setattr(leave_request_mod, "check_and_record", fake_check_and_record)
    repo = FakeLeaveRequestRepo()
    service = LeaveRequestService(repo=repo, employees=emp_repo, users=FakeUserRepo({USER["id"]: USER}))

    payload = LeaveRequestIn(employee_token=employee["request_token"], type="ferie", date_from="2026-08-01", date_to="2026-08-02")
    with pytest.raises(HTTPException) as exc_info:
        run(service.submit(payload))
    assert exc_info.value.status_code == 429
    assert "leave_request_token" in calls


def test_submit_rifiuta_intervallo_di_date_invertito(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    payload = LeaveRequestIn(
        employee_token=employee["request_token"], type="ferie",
        date_from="2026-08-10", date_to="2026-08-05",
    )
    with pytest.raises(ValidationAppError):
        run(service.submit(payload))


def test_submit_e_idempotente_su_doppio_invio_identico(monkeypatch):
    """Doppio clic / doppio invio della STESSA richiesta (stesso tipo e
    stesse date, ancora in attesa): non deve creare un secondo record."""
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    payload = LeaveRequestIn(
        employee_token=employee["request_token"], type="ferie",
        date_from="2026-08-10", date_to="2026-08-15",
    )
    run(service.submit(payload))
    run(service.submit(payload))
    assert len(repo.docs) == 1


def test_submit_non_deduplica_richieste_gia_decise(monkeypatch):
    """Se la richiesta identica precedente è già stata decisa, un nuovo
    invio è legittimo (es. ripresentata dopo un rifiuto) e va creato."""
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    payload = LeaveRequestIn(
        employee_token=employee["request_token"], type="ferie",
        date_from="2026-08-10", date_to="2026-08-15",
    )
    run(service.submit(payload))
    first_id = list(repo.docs.keys())[0]
    run(repo.update(first_id, USER["id"], {"status": "rifiutata"}))
    run(service.submit(payload))
    assert len(repo.docs) == 2


def test_list_requests_segnala_richieste_sovrapposte(monkeypatch):
    """Ferie 10-15 agosto e ferie 12-18 agosto per lo stesso dipendente:
    entrambe vengono create (non bloccate), ma segnalate come sovrapposte."""
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    run(service.submit(LeaveRequestIn(
        employee_token=employee["request_token"], type="ferie",
        date_from="2026-08-10", date_to="2026-08-15",
    )))
    run(service.submit(LeaveRequestIn(
        employee_token=employee["request_token"], type="ferie",
        date_from="2026-08-12", date_to="2026-08-18",
    )))
    assert len(repo.docs) == 2
    results = run(service.list_requests(USER))
    assert all(r["overlaps"] for r in results)


def test_list_requests_segnala_sovrapposizione_tra_tipi_diversi(monkeypatch):
    """Ferie sovrapposte a una malattia già approvata dello stesso
    dipendente: deve essere segnalata anche se il tipo è diverso."""
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    run(service.submit(LeaveRequestIn(
        employee_token=employee["request_token"], type="malattia",
        date_from="2026-08-10", date_to="2026-08-12",
    )))
    malattia_id = list(repo.docs.keys())[0]
    run(repo.update(malattia_id, USER["id"], {"status": "approvata"}))
    run(service.submit(LeaveRequestIn(
        employee_token=employee["request_token"], type="ferie",
        date_from="2026-08-11", date_to="2026-08-20",
    )))
    results = run(service.list_requests(USER))
    assert all(r["overlaps"] for r in results)


def test_list_requests_non_segnala_sovrapposizione_con_richiesta_rifiutata(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    run(service.submit(LeaveRequestIn(
        employee_token=employee["request_token"], type="ferie",
        date_from="2026-08-10", date_to="2026-08-15",
    )))
    first_id = list(repo.docs.keys())[0]
    run(repo.update(first_id, USER["id"], {"status": "rifiutata"}))
    run(service.submit(LeaveRequestIn(
        employee_token=employee["request_token"], type="ferie",
        date_from="2026-08-12", date_to="2026-08-18",
    )))
    results = run(service.list_requests(USER))
    assert not any(r["overlaps"] for r in results)


def test_list_requests_non_segnala_richieste_di_dipendenti_diversi(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    e1 = run(emp_service.create_employee(USER, make_employee("Mario Rossi")))
    e2 = run(emp_service.create_employee(USER, make_employee("Luca Bianchi")))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    run(service.submit(LeaveRequestIn(
        employee_token=e1["request_token"], type="ferie",
        date_from="2026-08-10", date_to="2026-08-15",
    )))
    run(service.submit(LeaveRequestIn(
        employee_token=e2["request_token"], type="ferie",
        date_from="2026-08-10", date_to="2026-08-15",
    )))
    results = run(service.list_requests(USER))
    assert not any(r["overlaps"] for r in results)


@pytest.mark.parametrize("date_from", ["2026-99-99", "2026-02-31", "test", "2026-8-2"])
def test_leave_request_in_rifiuta_date_non_valide(date_from):
    with pytest.raises(ValidationError):
        LeaveRequestIn(employee_token="tok", type="ferie", date_from=date_from, date_to="2026-08-05")


def test_submit_denormalizza_il_nome_del_dipendente(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee("Mario Rossi")))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    payload = LeaveRequestIn(
        employee_token=employee["request_token"], type="malattia",
        date_from="2026-08-01", date_to="2026-08-02",
    )
    run(service.submit(payload))
    saved = list(repo.docs.values())[0]
    assert saved["employee_name"] == "Mario Rossi"
    assert saved["status"] == "in_attesa"
    assert saved["user_id"] == USER["id"]


# ---------- leave_request_service.decide ----------

def test_decide_approva_una_richiesta_in_attesa(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    payload = LeaveRequestIn(employee_token=employee["request_token"], type="ferie", date_from="2026-08-01", date_to="2026-08-02")
    run(service.submit(payload))
    rid = list(repo.docs.keys())[0]

    run(service.decide(USER, rid, "approvata"))
    assert repo.docs[rid]["status"] == "approvata"
    assert repo.docs[rid]["decided_at"] is not None


def test_decide_blocca_una_seconda_decisione(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    payload = LeaveRequestIn(employee_token=employee["request_token"], type="ferie", date_from="2026-08-01", date_to="2026-08-02")
    run(service.submit(payload))
    rid = list(repo.docs.keys())[0]

    run(service.decide(USER, rid, "approvata"))
    with pytest.raises(ValidationAppError):
        run(service.decide(USER, rid, "rifiutata"))


class StaleReadLeaveRepo(FakeLeaveRequestRepo):
    """Simula la finestra della race condition: find_one restituisce
    sempre un'istantanea con status "in_attesa", indipendentemente dallo
    stato reale già scritto nel frattempo — come accadrebbe se due
    richieste HTTP quasi simultanee leggessero lo stato PRIMA che la
    prima decisione venga salvata. Serve a dimostrare che è l'update
    condizionale atomico in decide() (non il pre-check basato su questa
    lettura) a impedire la doppia decisione."""
    async def find_one(self, rid, user_id):
        d = self.docs.get(rid)
        if not d or d["user_id"] != user_id:
            return None
        stale = dict(d)
        stale["status"] = "in_attesa"
        return stale


def test_decide_e_atomico_contro_decisioni_concorrenti(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    monkeypatch.setattr(leave_request_mod, "send_email", _noop_send_email)
    monkeypatch.setattr(leave_request_mod, "check_and_record", lambda *a, **kw: _allow())
    repo = StaleReadLeaveRepo()
    service = LeaveRequestService(repo=repo, employees=emp_repo, users=FakeUserRepo({USER["id"]: USER}))

    payload = LeaveRequestIn(employee_token=employee["request_token"], type="ferie", date_from="2026-08-01", date_to="2026-08-02")
    run(service.submit(payload))
    rid = list(repo.docs.keys())[0]

    run(service.decide(USER, rid, "approvata"))
    assert repo.docs[rid]["status"] == "approvata"

    # Il pre-check basato sulla lettura stantia (sempre "in_attesa") la
    # lascerebbe passare; l'update atomico nel repository la blocca
    # perché lo stato reale non è più "in_attesa".
    with pytest.raises(ValidationAppError):
        run(service.decide(USER, rid, "rifiutata"))
    assert repo.docs[rid]["status"] == "approvata"


def test_decide_rifiuta_richiesta_di_un_altro_utente(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)
    payload = LeaveRequestIn(employee_token=employee["request_token"], type="ferie", date_from="2026-08-01", date_to="2026-08-02")
    run(service.submit(payload))
    rid = list(repo.docs.keys())[0]

    with pytest.raises(NotFoundError):
        run(service.decide({"id": "un-altro-utente"}, rid, "approvata"))


# ---------- leave_request_service.calendar ----------

def test_calendar_include_solo_le_richieste_approvate(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)

    run(service.submit(LeaveRequestIn(employee_token=employee["request_token"], type="ferie", date_from="2026-08-10", date_to="2026-08-12")))
    run(service.submit(LeaveRequestIn(employee_token=employee["request_token"], type="malattia", date_from="2026-08-15", date_to="2026-08-16")))
    ids = list(repo.docs.keys())
    run(service.decide(USER, ids[0], "approvata"))
    run(service.decide(USER, ids[1], "rifiutata"))

    result = run(service.calendar(USER, "2026-08"))
    assert len(result) == 1
    assert result[0]["status"] == "approvata"


def test_calendar_esclude_richieste_fuori_dal_mese(monkeypatch):
    emp_service, emp_repo = build_employee_service()
    employee = run(emp_service.create_employee(USER, make_employee()))
    service, repo = build_leave_service(monkeypatch, emp_repo)

    run(service.submit(LeaveRequestIn(employee_token=employee["request_token"], type="ferie", date_from="2026-07-10", date_to="2026-07-12")))
    rid = list(repo.docs.keys())[0]
    run(service.decide(USER, rid, "approvata"))

    assert run(service.calendar(USER, "2026-08")) == []
