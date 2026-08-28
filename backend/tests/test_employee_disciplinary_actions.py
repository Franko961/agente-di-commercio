"""
Verifica services/employee_disciplinary_action_service.py: le contestazioni
disciplinari registrate sulla scheda dipendente (richiami verbali, lettere di
richiamo, contestazioni, sospensioni) — elenco, creazione, modifica ed
eliminazione, incluso lo scoping per employee_id (a differenza di
employee_equipment/employee_compensation, qui find_one/update/delete
filtrano anche sull'employee_id dell'URL, non solo su id+user_id).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_employee_disciplinary_actions.py -v
"""

import asyncio
import sys
from datetime import date

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from core.exceptions import NotFoundError, ValidationAppError
from models.employee_disciplinary_action import EmployeeDisciplinaryActionIn
from services.employee_disciplinary_action_service import (
    EmployeeDisciplinaryActionService,
)


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


class FakeDisciplinaryActionRepo:
    def __init__(self):
        self.docs = {}

    async def find_many(self, employee_id, user_id):
        return [
            d
            for d in self.docs.values()
            if d["employee_id"] == employee_id and d["user_id"] == user_id
        ]

    async def find_one(self, aid, user_id, employee_id):
        d = self.docs.get(aid)
        return (
            d
            if d and d["user_id"] == user_id and d["employee_id"] == employee_id
            else None
        )

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, aid, user_id, employee_id, data):
        d = self.docs.get(aid)
        if not d or d["user_id"] != user_id or d["employee_id"] != employee_id:
            return False
        d.update(data)
        return True

    async def delete(self, aid, user_id, employee_id):
        d = self.docs.get(aid)
        if d and d["user_id"] == user_id and d["employee_id"] == employee_id:
            del self.docs[aid]


def build_service():
    da_repo = FakeDisciplinaryActionRepo()
    emp_repo = FakeEmployeeRepo()
    emp_repo.docs["emp-1"] = {"id": "emp-1", "user_id": USER["id"], "name": "Mario"}
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca"}
    service = EmployeeDisciplinaryActionService(repo=da_repo, employees=emp_repo)
    return service, da_repo, emp_repo


def make_payload(**overrides):
    data = dict(
        type="richiamo_verbale",
        subject="Ritardo ripetuto",
        contestation_date=date(2026, 6, 1),
    )
    data.update(overrides)
    return EmployeeDisciplinaryActionIn(**data)


# ---------- create_action ----------


def test_create_action_happy_path():
    service, da_repo, _ = build_service()

    item = run(
        service.create_action(
            USER, "emp-1", make_payload(description="Tre ritardi nell'ultimo mese")
        )
    )

    assert item["employee_id"] == "emp-1"
    assert item["user_id"] == USER["id"]
    assert item["type"] == "richiamo_verbale"
    assert item["subject"] == "Ritardo ripetuto"
    assert item["contestation_date"] == "2026-06-01"
    assert item["outcome"] == "in_attesa"
    assert item["description"] == "Tre ritardi nell'ultimo mese"
    assert item["document_id"] is None
    assert item["id"] in da_repo.docs


def test_create_action_rejects_unknown_employee():
    service, _, _ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.create_action(USER, "emp-does-not-exist", make_payload()))


def test_create_action_rejects_other_users_employee():
    service, _, _ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.create_action(OTHER_USER, "emp-1", make_payload()))


def test_create_action_strips_subject_and_notes():
    service, _, _ = build_service()
    item = run(
        service.create_action(
            USER, "emp-1", make_payload(subject="  Ritardo  ", notes="  nota  ")
        )
    )
    assert item["subject"] == "Ritardo"
    assert item["notes"] == "nota"


def test_create_action_persists_document_id():
    service, _, _ = build_service()
    item = run(
        service.create_action(USER, "emp-1", make_payload(document_id="doc-123"))
    )
    assert item["document_id"] == "doc-123"


# ---------- list_actions ----------


def test_list_actions_scoped_to_employee_and_user():
    service, _, _ = build_service()
    run(service.create_action(USER, "emp-1", make_payload(subject="Per emp-1")))
    run(service.create_action(USER, "emp-2", make_payload(subject="Per emp-2")))

    items = run(service.list_actions(USER, "emp-1"))
    assert len(items) == 1
    assert items[0]["subject"] == "Per emp-1"


def test_list_actions_rejects_unknown_employee():
    service, _, _ = build_service()
    with pytest.raises(ValidationAppError):
        run(service.list_actions(USER, "emp-does-not-exist"))


# ---------- EmployeeDisciplinaryActionIn: validazione ----------


def test_in_richiede_contestation_date():
    with pytest.raises(ValidationError):
        EmployeeDisciplinaryActionIn(type="richiamo_verbale", subject="Ritardo")


def test_in_azzera_justification_date_se_non_presentate():
    item = EmployeeDisciplinaryActionIn(
        type="richiamo_verbale",
        subject="Ritardo",
        contestation_date=date(2026, 6, 1),
        justification_submitted=False,
        justification_date=date(2026, 6, 5),
    )
    assert item.justification_date is None


def test_in_mantiene_justification_date_se_presentate():
    item = EmployeeDisciplinaryActionIn(
        type="richiamo_verbale",
        subject="Ritardo",
        contestation_date=date(2026, 6, 1),
        justification_submitted=True,
        justification_date=date(2026, 6, 5),
    )
    assert item.justification_date == date(2026, 6, 5)


# ---------- update_action ----------


def test_update_action_happy_path():
    service, da_repo, _ = build_service()
    item = run(service.create_action(USER, "emp-1", make_payload()))

    run(
        service.update_action(
            USER,
            "emp-1",
            item["id"],
            make_payload(outcome="sanzione_confermata", sanction="Multa"),
        )
    )

    updated = da_repo.docs[item["id"]]
    assert updated["outcome"] == "sanzione_confermata"
    assert updated["sanction"] == "Multa"
    assert updated["updated_at"] is not None


def test_update_action_unknown_raises_notfound():
    service, _, _ = build_service()
    with pytest.raises(NotFoundError):
        run(service.update_action(USER, "emp-1", "does-not-exist", make_payload()))


def test_update_action_wrong_employee_id_raises_notfound():
    # Stesso principio già corretto questa sessione per le sessioni presenze:
    # un id di record valido per l'account ma riferito con l'employee_id
    # sbagliato nell'URL non deve avere effetto (a differenza del bug ancora
    # presente in employee_equipment/employee_compensation).
    service, da_repo, _ = build_service()
    item = run(service.create_action(USER, "emp-1", make_payload()))

    with pytest.raises(NotFoundError):
        run(
            service.update_action(
                USER, "emp-2", item["id"], make_payload(outcome="archiviata")
            )
        )

    assert da_repo.docs[item["id"]]["outcome"] == "in_attesa"


def test_update_action_other_user_raises_notfound():
    service, da_repo, _ = build_service()
    item = run(service.create_action(USER, "emp-1", make_payload()))
    with pytest.raises(NotFoundError):
        run(service.update_action(OTHER_USER, "emp-1", item["id"], make_payload()))


# ---------- delete_action ----------


def test_delete_action_removes_item():
    service, da_repo, _ = build_service()
    item = run(service.create_action(USER, "emp-1", make_payload()))

    run(service.delete_action(USER, "emp-1", item["id"]))

    assert item["id"] not in da_repo.docs


def test_delete_action_wrong_employee_id_is_noop():
    service, da_repo, _ = build_service()
    item = run(service.create_action(USER, "emp-1", make_payload()))

    run(service.delete_action(USER, "emp-2", item["id"]))

    assert item["id"] in da_repo.docs


def test_delete_action_other_user_is_noop():
    service, da_repo, _ = build_service()
    item = run(service.create_action(USER, "emp-1", make_payload()))

    run(service.delete_action(OTHER_USER, "emp-1", item["id"]))

    assert item["id"] in da_repo.docs
