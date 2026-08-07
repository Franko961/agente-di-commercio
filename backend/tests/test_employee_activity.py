"""
Verifica services/employee_activity_service.py: la timeline "Attività"
della scheda dipendente è ricostruita al volo dai dati già esistenti
(nessuna collection di log dedicata) — copre assenze inviate/decise,
documenti caricati, dotazione aggiunta/restituita, compensi registrati.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_employee_activity.py -v
"""
import sys
import asyncio

import pytest

sys.path.insert(0, ".")

from core.exceptions import ValidationAppError
from services.employee_activity_service import EmployeeActivityService


def run(coro):
    return asyncio.run(coro)


USER = {"id": "user-1", "email": "manager@example.com"}
OTHER_USER = {"id": "user-2", "email": "altro@example.com"}


class FakeEmployeeRepo:
    def __init__(self):
        self.docs = {"emp-1": {"id": "emp-1", "user_id": USER["id"], "name": "Mario"}}

    async def find_one(self, eid, user_id):
        d = self.docs.get(eid)
        return d if d and d["user_id"] == user_id else None


class FakeLeaveRequestRepo:
    def __init__(self):
        self.docs = []

    async def find_by_employee(self, employee_id):
        return [d for d in self.docs if d["employee_id"] == employee_id]


class FakeListRepo:
    """Fake generico find_many(employee_id, user_id) — usato per
    documents/equipment/compensation, che condividono tutti la stessa forma."""
    def __init__(self):
        self.docs = []

    async def find_many(self, employee_id, user_id):
        return [d for d in self.docs if d["employee_id"] == employee_id and d["user_id"] == user_id]


def build_service():
    employees = FakeEmployeeRepo()
    leave_requests = FakeLeaveRequestRepo()
    documents = FakeListRepo()
    equipment = FakeListRepo()
    compensation = FakeListRepo()
    service = EmployeeActivityService(
        employees=employees, leave_requests=leave_requests,
        documents=documents, equipment=equipment, compensation=compensation,
    )
    return service, employees, leave_requests, documents, equipment, compensation


def test_get_activity_rejects_unknown_employee():
    service, *_ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.get_activity(USER, "emp-does-not-exist"))


def test_get_activity_rejects_other_users_employee():
    service, *_ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.get_activity(OTHER_USER, "emp-1"))


def test_get_activity_include_richiesta_inviata_e_decisa():
    service, _, leave_requests, *_ = build_service()
    leave_requests.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "type": "ferie",
        "date_from": "2026-08-10", "date_to": "2026-08-14",
        "status": "approvata", "created_at": "2026-08-01T10:00:00+00:00", "decided_at": "2026-08-02T09:00:00+00:00",
    })

    events = run(service.get_activity(USER, "emp-1"))

    types = [e["type"] for e in events]
    assert "assenza_inviata" in types
    assert "assenza_approvata" in types


def test_get_activity_richiesta_in_attesa_non_ha_evento_di_decisione():
    service, _, leave_requests, *_ = build_service()
    leave_requests.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "type": "malattia",
        "date_from": "2026-08-01", "date_to": "2026-08-03",
        "status": "in_attesa", "created_at": "2026-08-01T10:00:00+00:00", "decided_at": None,
    })

    events = run(service.get_activity(USER, "emp-1"))

    types = [e["type"] for e in events]
    assert types == ["assenza_inviata"]


def test_get_activity_include_documento_caricato():
    service, _, _, documents, *_ = build_service()
    documents.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "name": "Contratto 2026",
        "created_at": "2026-08-01T10:00:00+00:00",
    })

    events = run(service.get_activity(USER, "emp-1"))

    assert any(e["type"] == "documento_caricato" and "Contratto 2026" in e["detail"] for e in events)


def test_get_activity_dotazione_consegnata_non_restituita():
    service, _, _, _, equipment, _ = build_service()
    equipment.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "name": "Chiavi ufficio",
        "status": "consegnato", "returned_date": None, "created_at": "2026-08-01T10:00:00+00:00",
    })

    events = run(service.get_activity(USER, "emp-1"))

    types = [e["type"] for e in events]
    assert types == ["dotazione_aggiunta"]


def test_get_activity_dotazione_restituita_include_entrambi_gli_eventi():
    service, _, _, _, equipment, _ = build_service()
    equipment.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "name": "Divisa",
        "status": "restituito", "returned_date": "2026-08-06", "created_at": "2026-08-01T10:00:00+00:00",
    })

    events = run(service.get_activity(USER, "emp-1"))

    types = [e["type"] for e in events]
    assert "dotazione_aggiunta" in types
    assert "dotazione_restituita" in types


def test_get_activity_dotazione_restituita_usa_updated_at_timestamp_completo():
    # "at" deve essere un timestamp ISO completo come tutti gli altri
    # eventi (created_at/decided_at), non la stringa "AAAA-MM-DD" di
    # returned_date — vedi employee_equipment_service.update_equipment,
    # che ora imposta updated_at ad ogni modifica.
    service, _, _, _, equipment, _ = build_service()
    equipment.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "name": "Divisa",
        "status": "restituito", "returned_date": "2026-08-06",
        "created_at": "2026-08-01T10:00:00+00:00", "updated_at": "2026-08-06T15:30:00+00:00",
    })

    events = run(service.get_activity(USER, "emp-1"))

    ev = next(e for e in events if e["type"] == "dotazione_restituita")
    assert ev["at"] == "2026-08-06T15:30:00+00:00"


def test_get_activity_dotazione_restituita_ricade_su_created_at_se_senza_updated_at():
    # Dotazioni create prima dell'introduzione di updated_at: nessun
    # timestamp completo disponibile per l'evento di restituzione, meglio
    # usare created_at (comunque un timestamp completo, coerente col resto
    # della timeline) che lasciare la stringa di sola data.
    service, _, _, _, equipment, _ = build_service()
    equipment.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "name": "Divisa",
        "status": "restituito", "returned_date": "2026-08-06", "created_at": "2026-08-01T10:00:00+00:00",
    })

    events = run(service.get_activity(USER, "emp-1"))

    ev = next(e for e in events if e["type"] == "dotazione_restituita")
    assert ev["at"] == "2026-08-01T10:00:00+00:00"


def test_get_activity_include_compenso_registrato():
    service, _, _, _, _, compensation = build_service()
    compensation.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "type": "bonus", "amount": 450.0,
        "created_at": "2026-08-06T10:00:00+00:00",
    })

    events = run(service.get_activity(USER, "emp-1"))

    assert any(e["type"] == "compenso_registrato" and e["detail"] == "Bonus" for e in events)


def test_get_activity_ordinata_dal_piu_recente():
    service, _, leave_requests, documents, *_ = build_service()
    leave_requests.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "type": "ferie",
        "date_from": "2026-01-01", "date_to": "2026-01-02",
        "status": "in_attesa", "created_at": "2026-01-01T10:00:00+00:00", "decided_at": None,
    })
    documents.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "name": "Recente",
        "created_at": "2026-08-01T10:00:00+00:00",
    })

    events = run(service.get_activity(USER, "emp-1"))

    assert events[0]["detail"] == "Recente"


def test_get_activity_scoped_ad_altro_dipendente():
    service, employees, leave_requests, *_ = build_service()
    employees.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca"}
    leave_requests.docs.append({
        "user_id": USER["id"], "employee_id": "emp-2", "type": "ferie",
        "date_from": "2026-08-10", "date_to": "2026-08-14",
        "status": "in_attesa", "created_at": "2026-08-01T10:00:00+00:00", "decided_at": None,
    })

    events = run(service.get_activity(USER, "emp-1"))

    assert events == []
