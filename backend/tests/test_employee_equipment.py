"""
Verifica services/employee_equipment_service.py: la "Dotazione" assegnata a
un dipendente (divisa, DPI, telefono aziendale, chiavi, ecc.) sulla scheda
dipendente — elenco, creazione, modifica (incluso il cambio di stato
consegnato/restituito) ed eliminazione.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_employee_equipment.py -v
"""
import sys
import asyncio
from datetime import date

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from core.exceptions import NotFoundError, ValidationAppError
from models.employee_equipment import EmployeeEquipmentIn
from services.employee_equipment_service import EmployeeEquipmentService


def run(coro):
    return asyncio.run(coro)


USER = {"id": "user-1", "email": "manager@example.com"}
OTHER_USER = {"id": "user-2", "email": "altro@example.com"}


class FakeEmployeeRepo:
    def __init__(self):
        self.docs = {}

    async def find_one(self, eid, user_id):
        d = self.docs.get(eid)
        return d if d and d["user_id"] == user_id else None


class FakeEmployeeEquipmentRepo:
    def __init__(self):
        self.docs = {}

    async def find_many(self, employee_id, user_id):
        return [d for d in self.docs.values() if d["employee_id"] == employee_id and d["user_id"] == user_id]

    async def find_one(self, eqid, user_id):
        d = self.docs.get(eqid)
        return d if d and d["user_id"] == user_id else None

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, eqid, user_id, data):
        d = self.docs.get(eqid)
        if not d or d["user_id"] != user_id:
            return False
        d.update(data)
        return True

    async def delete(self, eqid, user_id):
        d = self.docs.get(eqid)
        if d and d["user_id"] == user_id:
            del self.docs[eqid]


def build_service():
    eq_repo = FakeEmployeeEquipmentRepo()
    emp_repo = FakeEmployeeRepo()
    emp_repo.docs["emp-1"] = {"id": "emp-1", "user_id": USER["id"], "name": "Mario"}
    service = EmployeeEquipmentService(repo=eq_repo, employees=emp_repo)
    return service, eq_repo, emp_repo


# ---------- create_equipment ----------

def test_create_equipment_happy_path():
    service, eq_repo, _ = build_service()

    item = run(service.create_equipment(USER, "emp-1", EmployeeEquipmentIn(
        name="Divisa taglia L", delivered_date=date(2026, 1, 10), notes="consegnata in ufficio",
    )))

    assert item["employee_id"] == "emp-1"
    assert item["user_id"] == USER["id"]
    assert item["name"] == "Divisa taglia L"
    assert item["delivered_date"] == "2026-01-10"
    assert item["returned_date"] is None
    assert item["status"] == "consegnato"
    assert item["notes"] == "consegnata in ufficio"


def test_create_equipment_rejects_unknown_employee():
    service, _, _ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.create_equipment(USER, "emp-does-not-exist", EmployeeEquipmentIn(name="Chiavi")))


def test_create_equipment_rejects_other_users_employee():
    service, _, _ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.create_equipment(OTHER_USER, "emp-1", EmployeeEquipmentIn(name="Chiavi")))


def test_create_equipment_strips_name_and_notes():
    service, eq_repo, _ = build_service()
    item = run(service.create_equipment(USER, "emp-1", EmployeeEquipmentIn(name="  Casco DPI  ", notes="  nota  ")))
    assert item["name"] == "Casco DPI"
    assert item["notes"] == "nota"


def test_create_equipment_imposta_updated_at_uguale_a_created_at():
    # employee_activity_service usa updated_at (timestamp completo) per
    # l'evento "dotazione restituita" nella timeline, invece della sola
    # data returned_date — vedi test_employee_activity.py.
    service, eq_repo, _ = build_service()
    item = run(service.create_equipment(USER, "emp-1", EmployeeEquipmentIn(name="Chiavi")))
    assert item["updated_at"] == item["created_at"]


# ---------- list_equipment ----------

def test_list_equipment_scoped_to_employee_and_user():
    service, eq_repo, emp_repo = build_service()
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca"}
    run(service.create_equipment(USER, "emp-1", EmployeeEquipmentIn(name="Telefono aziendale")))
    run(service.create_equipment(USER, "emp-2", EmployeeEquipmentIn(name="Furgone kit primo soccorso")))

    items = run(service.list_equipment(USER, "emp-1"))
    assert len(items) == 1
    assert items[0]["name"] == "Telefono aziendale"


def test_list_equipment_rejects_unknown_employee():
    service, _, _ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.list_equipment(USER, "emp-does-not-exist"))


# ---------- EmployeeEquipmentIn: coerenza stato/date ----------

def test_equipment_in_restituito_richiede_returned_date():
    with pytest.raises(ValidationError, match="data di restituzione è obbligatoria"):
        EmployeeEquipmentIn(name="Chiavi", status="restituito")


def test_equipment_in_rifiuta_returned_date_precedente_a_delivered_date():
    with pytest.raises(ValidationError, match="non può essere precedente"):
        EmployeeEquipmentIn(
            name="Chiavi", status="restituito",
            delivered_date=date(2026, 6, 1), returned_date=date(2026, 1, 1),
        )


def test_equipment_in_accetta_returned_date_uguale_a_delivered_date():
    item = EmployeeEquipmentIn(
        name="Chiavi", status="restituito",
        delivered_date=date(2026, 6, 1), returned_date=date(2026, 6, 1),
    )
    assert item.returned_date == date(2026, 6, 1)


def test_equipment_in_consegnato_azzera_returned_date_residuo():
    # Es. la stessa dotazione viene rimessa in consegna dopo essere stata
    # segnata restituita, ma il form non svuota il campo data da solo.
    item = EmployeeEquipmentIn(
        name="Chiavi", status="consegnato",
        delivered_date=date(2026, 1, 1), returned_date=date(2026, 6, 1),
    )
    assert item.returned_date is None


def test_equipment_in_consegnato_senza_date_e_ok():
    item = EmployeeEquipmentIn(name="Chiavi", status="consegnato")
    assert item.returned_date is None


# ---------- update_equipment ----------

def test_update_equipment_marks_returned():
    service, eq_repo, _ = build_service()
    item = run(service.create_equipment(USER, "emp-1", EmployeeEquipmentIn(name="Chiavi ufficio", delivered_date=date(2026, 1, 1))))

    run(service.update_equipment(USER, item["id"], EmployeeEquipmentIn(
        name="Chiavi ufficio", delivered_date=date(2026, 1, 1),
        returned_date=date(2026, 6, 1), status="restituito",
    )))

    updated = eq_repo.docs[item["id"]]
    assert updated["status"] == "restituito"
    assert updated["returned_date"] == "2026-06-01"
    assert updated["updated_at"] is not None


def test_update_equipment_unknown_raises_404():
    service, _, _ = build_service()
    with pytest.raises(NotFoundError):
        run(service.update_equipment(USER, "does-not-exist", EmployeeEquipmentIn(name="x")))


def test_update_equipment_other_user_raises_404():
    service, eq_repo, _ = build_service()
    item = run(service.create_equipment(USER, "emp-1", EmployeeEquipmentIn(name="Chiavi")))
    with pytest.raises(NotFoundError):
        run(service.update_equipment(OTHER_USER, item["id"], EmployeeEquipmentIn(name="Chiavi")))


# ---------- delete_equipment ----------

def test_delete_equipment_removes_item():
    service, eq_repo, _ = build_service()
    item = run(service.create_equipment(USER, "emp-1", EmployeeEquipmentIn(name="Chiavi")))

    run(service.delete_equipment(USER, item["id"]))

    assert item["id"] not in eq_repo.docs
    assert run(service.list_equipment(USER, "emp-1")) == []


def test_delete_equipment_other_user_is_noop():
    service, eq_repo, _ = build_service()
    item = run(service.create_equipment(USER, "emp-1", EmployeeEquipmentIn(name="Chiavi")))

    run(service.delete_equipment(OTHER_USER, item["id"]))

    assert item["id"] in eq_repo.docs
