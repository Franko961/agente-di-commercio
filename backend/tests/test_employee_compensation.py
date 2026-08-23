"""
Verifica services/employee_compensation_service.py: storico compensi
(stipendio/bonus/rimborso) per dipendente sulla scheda dipendente, con
sincronizzazione bidirezionale verso Spese — stesso pattern già validato
per i costi Flotta (vedi vehicle_cost_service.py in test_flotta_module.py).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_employee_compensation.py -v
"""
import sys
import asyncio
from datetime import date

import pytest

sys.path.insert(0, ".")

from core.exceptions import NotFoundError, ValidationAppError
from models.employee_compensation import EmployeeCompensationIn
from services.employee_compensation_service import EmployeeCompensationService


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


class FakeEmployeeCompensationRepo:
    def __init__(self):
        self.docs = {}

    async def find_many(self, employee_id, user_id):
        return [d for d in self.docs.values() if d["employee_id"] == employee_id and d["user_id"] == user_id]

    async def find_one(self, cid, user_id, employee_id):
        d = self.docs.get(cid)
        return d if d and d["user_id"] == user_id and d["employee_id"] == employee_id else None

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, cid, user_id, employee_id, data):
        d = self.docs.get(cid)
        if not d or d["user_id"] != user_id or d["employee_id"] != employee_id:
            return False
        d.update(data)
        return True

    async def delete(self, cid, user_id, employee_id):
        d = self.docs.get(cid)
        if d and d["user_id"] == user_id and d["employee_id"] == employee_id:
            del self.docs[cid]


class FakeExpenseRepo:
    def __init__(self):
        self.docs = {}

    async def find_one(self, eid, user_id):
        d = self.docs.get(eid)
        return d if d and d["user_id"] == user_id else None

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, eid, user_id, data):
        d = self.docs.get(eid)
        if d and d["user_id"] == user_id:
            d.update(data)

    async def delete(self, eid, user_id):
        d = self.docs.get(eid)
        if d and d["user_id"] == user_id:
            del self.docs[eid]


def build_service():
    comp_repo = FakeEmployeeCompensationRepo()
    emp_repo = FakeEmployeeRepo()
    expense_repo = FakeExpenseRepo()
    emp_repo.docs["emp-1"] = {"id": "emp-1", "user_id": USER["id"], "name": "Mario", "surname": "Rossi"}
    service = EmployeeCompensationService(repo=comp_repo, employees=emp_repo, expenses=expense_repo)
    return service, comp_repo, emp_repo, expense_repo


# ---------- create_compensation (+ sync su Spese) ----------

def test_create_compensation_genera_spesa_collegata():
    service, comp_repo, _, expense_repo = build_service()

    comp = run(service.create_compensation(USER, "emp-1", EmployeeCompensationIn(
        type="stipendio", amount=1500, date=date(2026, 1, 31), notes="gennaio",
    )))

    assert comp["employee_id"] == "emp-1"
    assert comp["type"] == "stipendio"
    assert comp["amount"] == 1500
    assert comp["date"] == "2026-01-31"
    assert comp["expense_id"] in expense_repo.docs

    expense = expense_repo.docs[comp["expense_id"]]
    assert expense["source"] == "personale"
    assert expense["employee_compensation_id"] == comp["id"]
    assert expense["category"] == "altro"
    assert expense["amount"] == 1500
    assert "Mario Rossi" in expense["description"]
    assert "Stipendio" in expense["description"]
    assert "gennaio" in expense["description"]


def test_create_compensation_rejects_unknown_employee():
    service, _, _, _ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.create_compensation(USER, "emp-does-not-exist", EmployeeCompensationIn(amount=100, date=date(2026, 1, 1))))


def test_create_compensation_rejects_other_users_employee():
    service, _, _, _ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.create_compensation(OTHER_USER, "emp-1", EmployeeCompensationIn(amount=100, date=date(2026, 1, 1))))


def test_compensation_in_rifiuta_importo_non_positivo():
    with pytest.raises(Exception):
        EmployeeCompensationIn(amount=0, date=date(2026, 1, 1))
    with pytest.raises(Exception):
        EmployeeCompensationIn(amount=-50, date=date(2026, 1, 1))


def test_create_compensation_rollback_spesa_se_insert_compenso_fallisce():
    # Niente transazione Mongo sul flusso a due scritture (insert spesa, poi
    # insert compenso): senza rollback esplicito, un fallimento qui
    # lascerebbe la spesa orfana per sempre — vedi services/reconciliation_service.py.
    service, comp_repo, _, expense_repo = build_service()

    async def failing_insert(doc):
        raise RuntimeError("scrittura del compenso fallita")
    comp_repo.insert = failing_insert

    with pytest.raises(RuntimeError):
        run(service.create_compensation(USER, "emp-1", EmployeeCompensationIn(
            type="stipendio", amount=1500, date=date(2026, 8, 1),
        )))
    assert expense_repo.docs == {}


# ---------- list_compensations ----------

def test_list_compensations_scoped_to_employee_and_user():
    service, _, emp_repo, _ = build_service()
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca", "surname": "Bianchi"}
    run(service.create_compensation(USER, "emp-1", EmployeeCompensationIn(amount=1000, date=date(2026, 1, 1))))
    run(service.create_compensation(USER, "emp-2", EmployeeCompensationIn(amount=2000, date=date(2026, 1, 1))))

    items = run(service.list_compensations(USER, "emp-1"))
    assert len(items) == 1
    assert items[0]["amount"] == 1000


def test_list_compensations_rejects_unknown_employee():
    service, _, _, _ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.list_compensations(USER, "emp-does-not-exist"))


# ---------- update_compensation (+ sync su Spese) ----------

def test_update_compensation_sincronizza_la_spesa_collegata():
    service, comp_repo, _, expense_repo = build_service()
    comp = run(service.create_compensation(USER, "emp-1", EmployeeCompensationIn(type="bonus", amount=200, date=date(2026, 2, 1))))

    run(service.update_compensation(USER, "emp-1", comp["id"], EmployeeCompensationIn(type="bonus", amount=350, date=date(2026, 2, 15), notes="produttività")))

    updated = comp_repo.docs[comp["id"]]
    assert updated["amount"] == 350
    assert updated["date"] == "2026-02-15"

    expense = expense_repo.docs[comp["expense_id"]]
    assert expense["amount"] == 350
    assert expense["date"] == "2026-02-15"
    assert "produttività" in expense["description"]


def test_update_compensation_unknown_raises_404():
    service, _, _, _ = build_service()
    with pytest.raises(NotFoundError):
        run(service.update_compensation(USER, "emp-1", "does-not-exist", EmployeeCompensationIn(amount=100, date=date(2026, 1, 1))))


def test_update_compensation_other_user_raises_404():
    service, _, _, _ = build_service()
    comp = run(service.create_compensation(USER, "emp-1", EmployeeCompensationIn(amount=100, date=date(2026, 1, 1))))
    with pytest.raises(NotFoundError):
        run(service.update_compensation(OTHER_USER, "emp-1", comp["id"], EmployeeCompensationIn(amount=100, date=date(2026, 1, 1))))


def test_update_compensation_wrong_employee_id_raises_404():
    # Bug di isolamento corretto: un id di record valido per l'account ma
    # riferito con l'employee_id sbagliato nell'URL non deve avere effetto.
    service, comp_repo, emp_repo, _ = build_service()
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca", "surname": "Bianchi"}
    comp = run(service.create_compensation(USER, "emp-1", EmployeeCompensationIn(amount=100, date=date(2026, 1, 1))))

    with pytest.raises(NotFoundError):
        run(service.update_compensation(USER, "emp-2", comp["id"], EmployeeCompensationIn(amount=999, date=date(2026, 1, 1))))

    assert comp_repo.docs[comp["id"]]["amount"] == 100


# ---------- delete_compensation (+ sync su Spese) ----------

def test_delete_compensation_rimuove_anche_la_spesa_collegata():
    service, comp_repo, _, expense_repo = build_service()
    comp = run(service.create_compensation(USER, "emp-1", EmployeeCompensationIn(amount=100, date=date(2026, 1, 1))))
    expense_id = comp["expense_id"]

    run(service.delete_compensation(USER, "emp-1", comp["id"]))

    assert comp["id"] not in comp_repo.docs
    assert expense_id not in expense_repo.docs


def test_delete_compensation_other_user_is_noop():
    service, comp_repo, _, expense_repo = build_service()
    comp = run(service.create_compensation(USER, "emp-1", EmployeeCompensationIn(amount=100, date=date(2026, 1, 1))))

    run(service.delete_compensation(OTHER_USER, "emp-1", comp["id"]))

    assert comp["id"] in comp_repo.docs
    assert comp["expense_id"] in expense_repo.docs


def test_delete_compensation_wrong_employee_id_is_noop():
    service, comp_repo, emp_repo, expense_repo = build_service()
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca", "surname": "Bianchi"}
    comp = run(service.create_compensation(USER, "emp-1", EmployeeCompensationIn(amount=100, date=date(2026, 1, 1))))

    run(service.delete_compensation(USER, "emp-2", comp["id"]))

    assert comp["id"] in comp_repo.docs
    assert comp["expense_id"] in expense_repo.docs
