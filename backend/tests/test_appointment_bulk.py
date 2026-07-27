"""
Test per la creazione in blocco degli appuntamenti
(services.appointment_service.create_many), usata dal pulsante "Salva il
giro in Agenda" del pianificatore visite.

Esegui con:
    python -m pytest tests/test_appointment_bulk.py -v
"""
import sys
import asyncio

import pytest

sys.path.insert(0, ".")

from services.appointment_service import AppointmentService
from models.appointment import AppointmentIn, AppointmentBulkIn


def run(coro):
    return asyncio.run(coro)


class FakeAppointmentRepo:
    def __init__(self):
        self.docs = []

    async def insert(self, doc):
        self.docs.append(doc)
        return doc


class FakeGoogleCalendarService:
    def __init__(self):
        self.pushed = []

    async def push_create(self, user_id, appointment):
        self.pushed.append((user_id, appointment["id"]))


def build_service(monkeypatch, fake_google):
    repo = FakeAppointmentRepo()
    service = AppointmentService(repo=repo)

    # _push_to_google_calendar_safe fa `from services.google_calendar_service
    # import google_calendar_service` dentro il metodo (import locale, per
    # evitare un ciclo di import tra i due servizi): patchando l'attributo sul
    # modulo, il lookup a runtime prende comunque il nostro fake.
    import services.google_calendar_service as gcal_mod
    monkeypatch.setattr(gcal_mod, "google_calendar_service", fake_google)

    return service, repo


USER = {"id": "user-1"}


def test_create_many_crea_un_appuntamento_per_tappa(monkeypatch):
    fake_google = FakeGoogleCalendarService()
    service, repo = build_service(monkeypatch, fake_google)

    payloads = [
        AppointmentIn(client_id="c1", title="Visita: Cliente Uno", start="2026-07-28T09:00:00.000Z"),
        AppointmentIn(client_id="c2", title="Visita: Cliente Due", start="2026-07-28T09:30:00.000Z"),
        AppointmentIn(client_id="c3", title="Visita: Cliente Tre", start="2026-07-28T10:00:00.000Z"),
    ]

    created = run(service.create_many(USER, payloads))

    assert len(created) == 3
    assert len(repo.docs) == 3
    assert {d["client_id"] for d in repo.docs} == {"c1", "c2", "c3"}
    assert all(d["user_id"] == "user-1" for d in repo.docs)
    assert all("id" in d and "created_at" in d for d in repo.docs)
    # La sync verso Google deve avvenire per OGNI appuntamento, non una sola
    # volta in blocco (push_create richiede l'id locale già assegnato).
    assert len(fake_google.pushed) == 3


def test_create_many_lista_vuota_non_crea_nulla(monkeypatch):
    fake_google = FakeGoogleCalendarService()
    service, repo = build_service(monkeypatch, fake_google)

    created = run(service.create_many(USER, []))

    assert created == []
    assert repo.docs == []
    assert fake_google.pushed == []


def test_appointment_bulk_in_rifiuta_lista_vuota():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AppointmentBulkIn(appointments=[])


def test_appointment_bulk_in_rifiuta_piu_di_max_clienti():
    from pydantic import ValidationError
    many = [AppointmentIn(title=f"Visita {i}", start="2026-07-28T09:00:00.000Z") for i in range(51)]
    with pytest.raises(ValidationError):
        AppointmentBulkIn(appointments=many)

    ok = [AppointmentIn(title=f"Visita {i}", start="2026-07-28T09:00:00.000Z") for i in range(50)]
    AppointmentBulkIn(appointments=ok)  # non deve sollevare


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
