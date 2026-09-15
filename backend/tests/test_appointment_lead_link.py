"""
Test per il collegamento appuntamento-lead
(services.appointment_service.create_appointment con lead_id) — permette di
vedere in Agenda un appuntamento fissato con un lead non ancora cliente.

Esegui con:
    python -m pytest tests/test_appointment_lead_link.py -v
"""

import asyncio
import sys

import pytest

sys.path.insert(0, ".")

from models.appointment import AppointmentIn
from services.appointment_service import AppointmentService


def run(coro):
    return asyncio.run(coro)


class FakeAppointmentRepo:
    def __init__(self):
        self.docs = []

    async def insert(self, doc):
        self.docs.append(doc)
        return doc


class FakeLeadRepo:
    def __init__(self):
        self.updates = []

    async def update(self, lid, user_id, data):
        self.updates.append((lid, user_id, data))


class FakeGoogleCalendarService:
    def __init__(self):
        self.pushed = []

    async def push_create(self, user_id, appointment):
        self.pushed.append((user_id, appointment["id"]))


def build_service(monkeypatch, fake_google):
    repo = FakeAppointmentRepo()
    lead_repo = FakeLeadRepo()
    service = AppointmentService(repo=repo, lead_repo=lead_repo)

    import services.google_calendar_service as gcal_mod

    monkeypatch.setattr(gcal_mod, "google_calendar_service", fake_google)

    return service, repo, lead_repo


USER = {"id": "user-1"}


def test_create_appointment_con_lead_id_aggiorna_last_interaction_at(monkeypatch):
    fake_google = FakeGoogleCalendarService()
    service, repo, lead_repo = build_service(monkeypatch, fake_google)

    payload = AppointmentIn(
        lead_id="lead-1",
        title="Primo incontro",
        start="2026-09-20T09:00:00.000Z",
    )

    created = run(service.create_appointment(USER, payload))

    assert created["lead_id"] == "lead-1"
    assert len(lead_repo.updates) == 1
    lid, user_id, data = lead_repo.updates[0]
    assert lid == "lead-1"
    assert user_id == "user-1"
    assert "last_interaction_at" in data


def test_create_appointment_senza_lead_id_non_tocca_il_lead_repo(monkeypatch):
    fake_google = FakeGoogleCalendarService()
    service, repo, lead_repo = build_service(monkeypatch, fake_google)

    payload = AppointmentIn(
        client_id="client-1",
        title="Visita cliente",
        start="2026-09-20T09:00:00.000Z",
    )

    created = run(service.create_appointment(USER, payload))

    assert created["client_id"] == "client-1"
    assert created["lead_id"] is None
    assert lead_repo.updates == []


def test_appointment_in_accetta_lead_id_opzionale():
    a = AppointmentIn(title="Senza contatto", start="2026-09-20T09:00:00.000Z")
    assert a.lead_id is None

    b = AppointmentIn(
        title="Con lead", start="2026-09-20T09:00:00.000Z", lead_id="lead-2"
    )
    assert b.lead_id == "lead-2"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
