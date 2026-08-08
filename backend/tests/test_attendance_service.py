"""
Verifica services/attendance_service.py: rilevazione presenze v1 tramite
chiosco pubblico (QR uguale per tutti i dipendenti, affisso all'ingresso
dell'azienda + PIN a 4 cifre per identificare chi timbra — vedi il
docstring della classe per il perché niente geolocalizzazione né link
personale), più la gestione lato responsabile (elenco/inserimento
manuale/correzione/eliminazione di una sessione, generazione QR e PIN).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_attendance_service.py -v
"""
import sys
import csv
import io
import asyncio

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from core.exceptions import NotFoundError, ValidationAppError
from core.security import hash_password
from models.attendance import AttendanceCorrectionIn
from services.attendance_service import AttendanceService


def run(coro):
    return asyncio.run(coro)


def _rows_from_response(response):
    """Stesso helper usato in test_csv_export_injection.py: consuma lo
    StreamingResponse di csv_response e lo riconverte in righe (liste di
    stringhe) per poterle confrontare nei test."""
    async def _collect():
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        return chunks
    chunks = asyncio.run(_collect())
    text = "".join(chunks).lstrip("﻿")
    return list(csv.reader(io.StringIO(text), delimiter=";"))


USER = {
    "id": "user-1", "email": "manager@example.com", "enabled_extra_modules": ["personale"],
    "attendance_kiosk_token_hash": "hash-del-token-azienda",
}
OTHER_USER = {"id": "user-2", "email": "altro@example.com", "enabled_extra_modules": ["personale"]}
KIOSK_TOKEN = "il-token-azienda"
PIN = "4242"


class FakeEmployeeRepo:
    def __init__(self):
        self.docs = {}

    async def find_one(self, eid, user_id):
        d = self.docs.get(eid)
        if not d or d["user_id"] != user_id:
            return None
        return {k: v for k, v in d.items() if k != "pin_hash"}

    async def find_one_with_pin_hash(self, eid, user_id):
        d = self.docs.get(eid)
        return d if d and d["user_id"] == user_id else None

    async def find_many(self, user_id):
        return [{k: v for k, v in d.items() if k != "pin_hash"} for d in self.docs.values() if d["user_id"] == user_id]

    async def update(self, eid, user_id, data):
        d = self.docs.get(eid)
        if not d or d["user_id"] != user_id:
            return False
        d.update(data)
        return True


class FakeUserRepo:
    def __init__(self):
        self.docs = {}

    async def find_by_id(self, uid):
        return self.docs.get(uid)

    async def find_by_attendance_kiosk_token_hash(self, token_hash):
        for d in self.docs.values():
            if d.get("attendance_kiosk_token_hash") == token_hash:
                return d
        return None

    async def update_by_id(self, uid, data):
        if uid in self.docs:
            self.docs[uid].update(data)


class FakeAttendanceRepo:
    def __init__(self):
        self.docs = {}

    async def find_many(self, employee_id, user_id):
        return sorted(
            (d for d in self.docs.values() if d["employee_id"] == employee_id and d["user_id"] == user_id),
            key=lambda d: d["clock_in"], reverse=True,
        )

    async def find_one(self, sid, user_id):
        d = self.docs.get(sid)
        return d if d and d["user_id"] == user_id else None

    async def find_open_session(self, employee_id, user_id):
        for d in self.docs.values():
            if d["employee_id"] == employee_id and d["user_id"] == user_id and d["clock_out"] is None:
                return d
        return None

    async def find_all_closed(self, user_id):
        return [
            {
                "employee_id": d["employee_id"], "employee_name": d.get("employee_name", ""),
                "clock_in": d["clock_in"], "clock_out": d["clock_out"], "note": d.get("note", ""),
            }
            for d in self.docs.values() if d["user_id"] == user_id and d["clock_out"] is not None
        ]

    async def insert(self, doc):
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, sid, user_id, data):
        d = self.docs.get(sid)
        if not d or d["user_id"] != user_id:
            return False
        d.update(data)
        return True

    async def delete(self, sid, user_id):
        d = self.docs.get(sid)
        if d and d["user_id"] == user_id:
            del self.docs[sid]


class FakeLeaveRequestRepo:
    def __init__(self):
        self.docs = []

    async def find_overlapping(self, user_id, date_from, date_to, status="approvata"):
        return [
            dict(r) for r in self.docs
            if r["user_id"] == user_id and r["status"] == status
            and r["date_from"] <= date_to and r["date_to"] >= date_from
        ]


async def _always_ok(*args, **kwargs):
    return True


def build_service(monkeypatch, with_pin=True):
    att_repo = FakeAttendanceRepo()
    emp_repo = FakeEmployeeRepo()
    emp_repo.docs["emp-1"] = {
        "id": "emp-1", "user_id": USER["id"], "name": "Mario", "surname": "Rossi", "active": True,
        "pin_hash": hash_password(PIN) if with_pin else None,
    }
    user_repo = FakeUserRepo()
    user_repo.docs[USER["id"]] = dict(USER)
    user_repo.docs[OTHER_USER["id"]] = dict(OTHER_USER)
    leave_repo = FakeLeaveRequestRepo()
    service = AttendanceService(repo=att_repo, employees=emp_repo, users=user_repo, leave_requests=leave_repo)

    import services.attendance_service as attendance_mod
    monkeypatch.setattr(attendance_mod, "hash_reset_token", lambda t: "hash-del-token-azienda" if t == KIOSK_TOKEN else "altro")
    monkeypatch.setattr(attendance_mod, "check_and_record", _always_ok)
    return service, att_repo, emp_repo, user_repo, leave_repo


# ---------- QR aziendale ----------

def test_get_kiosk_token_status_riflette_se_generato(monkeypatch):
    service, _, _, user_repo, _ = build_service(monkeypatch)
    assert run(service.get_kiosk_token_status(USER)) == {"has_token": True}
    assert run(service.get_kiosk_token_status(OTHER_USER)) == {"has_token": False}


def test_regenerate_kiosk_token_salva_solo_lhash(monkeypatch):
    service, _, _, user_repo, _ = build_service(monkeypatch)
    token = run(service.regenerate_kiosk_token(OTHER_USER))
    assert token
    stored = user_repo.docs[OTHER_USER["id"]]["attendance_kiosk_token_hash"]
    assert stored != token  # mai salvato in chiaro


# ---------- PIN dipendente ----------

def test_set_employee_pin_genera_un_pin_verificabile(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    pin = run(service.set_employee_pin(USER, "emp-1"))
    assert len(pin) == 4 and pin.isdigit()
    assert emp_repo.docs["emp-1"]["pin_hash"] != pin  # mai salvato in chiaro


def test_set_employee_pin_rejects_unknown_employee(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    with pytest.raises(ValidationAppError):
        run(service.set_employee_pin(USER, "emp-does-not-exist"))


def test_employee_has_pin_riflette_lo_stato(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch, with_pin=False)
    assert run(service.employee_has_pin(USER, "emp-1")) is False

    run(service.set_employee_pin(USER, "emp-1"))
    assert run(service.employee_has_pin(USER, "emp-1")) is True


# ---------- list_kiosk_employees ----------

def test_list_kiosk_employees_restituisce_solo_attivi_con_stato(monkeypatch):
    service, att_repo, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca", "active": False, "pin_hash": None}

    employees = run(service.list_kiosk_employees(KIOSK_TOKEN))

    assert len(employees) == 1
    assert employees[0] == {"id": "emp-1", "name": "Mario Rossi", "clocked_in": False}


def test_list_kiosk_employees_rifiuta_token_non_valido(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    with pytest.raises(NotFoundError):
        run(service.list_kiosk_employees("token-sbagliato"))


# ---------- clock_in_kiosk / clock_out_kiosk ----------

def test_clock_in_kiosk_con_pin_corretto_crea_sessione(monkeypatch):
    service, att_repo, _, _, _ = build_service(monkeypatch)
    session = run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))
    assert session["employee_id"] == "emp-1"
    assert session["clock_out"] is None
    assert session["corrected_by_admin"] is False


def test_clock_in_kiosk_rifiuta_pin_errato(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    with pytest.raises(ValidationAppError, match="PIN"):
        run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", "0000"))


def test_clock_in_kiosk_rifiuta_se_dipendente_senza_pin_impostato(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch, with_pin=False)
    with pytest.raises(ValidationAppError, match="PIN"):
        run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))


def test_clock_in_kiosk_rifiuta_se_gia_in_servizio(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))
    with pytest.raises(ValidationAppError, match="già in servizio"):
        run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))


def test_clock_out_kiosk_chiude_la_sessione_aperta(monkeypatch):
    service, att_repo, _, _, _ = build_service(monkeypatch)
    session = run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))
    closed = run(service.clock_out_kiosk(KIOSK_TOKEN, "emp-1", PIN))
    assert closed["id"] == session["id"]
    assert att_repo.docs[session["id"]]["clock_out"] is not None


def test_clock_out_kiosk_rifiuta_se_nessuna_sessione_aperta(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    with pytest.raises(ValidationAppError):
        run(service.clock_out_kiosk(KIOSK_TOKEN, "emp-1", PIN))


def test_clock_in_kiosk_rifiuta_token_non_valido(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    with pytest.raises(NotFoundError):
        run(service.clock_in_kiosk("token-sbagliato", "emp-1", PIN))


def test_clock_in_kiosk_rifiuta_se_dipendente_disattivato(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"]["active"] = False
    with pytest.raises(NotFoundError):
        run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))


def test_clock_in_kiosk_rifiuta_se_modulo_personale_disattivato(monkeypatch):
    service, _, _, user_repo, _ = build_service(monkeypatch)
    user_repo.docs[USER["id"]]["enabled_extra_modules"] = []
    with pytest.raises(NotFoundError):
        run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))


# ---------- lato admin ----------

def test_list_sessions_scoped_a_dipendente_e_utente(monkeypatch):
    service, att_repo, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca", "active": True, "pin_hash": None}
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00", clock_out="2026-08-01T17:00:00+00:00",
    )))
    run(service.create_manual_session(USER, "emp-2", AttendanceCorrectionIn(
        clock_in="2026-08-01T09:00:00+00:00", clock_out="2026-08-01T18:00:00+00:00",
    )))

    sessions = run(service.list_sessions(USER, "emp-1"))
    assert len(sessions) == 1
    assert sessions[0]["employee_id"] == "emp-1"


def test_create_manual_session_marca_corretta_da_admin(monkeypatch):
    service, att_repo, _, _, _ = build_service(monkeypatch)
    session = run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00", clock_out="2026-08-01T17:00:00+00:00", note="dimenticato",
    )))
    assert session["corrected_by_admin"] is True
    assert session["note"] == "dimenticato"


def test_create_manual_session_rejects_unknown_employee(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    with pytest.raises(ValidationAppError):
        run(service.create_manual_session(USER, "emp-does-not-exist", AttendanceCorrectionIn(
            clock_in="2026-08-01T08:00:00+00:00",
        )))


def test_correct_session_aggiorna_orari_e_marca_corretta(monkeypatch):
    service, att_repo, _, _, _ = build_service(monkeypatch)
    session = run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))

    run(service.correct_session(USER, session["id"], AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00", clock_out="2026-08-01T17:00:00+00:00", note="orario corretto",
    )))

    updated = att_repo.docs[session["id"]]
    assert updated["clock_in"] == "2026-08-01T08:00:00+00:00"
    assert updated["clock_out"] == "2026-08-01T17:00:00+00:00"
    assert updated["corrected_by_admin"] is True


def test_correct_session_unknown_raises_404(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    with pytest.raises(NotFoundError):
        run(service.correct_session(USER, "does-not-exist", AttendanceCorrectionIn(
            clock_in="2026-08-01T08:00:00+00:00",
        )))


def test_delete_session_removes_it(monkeypatch):
    service, att_repo, _, _, _ = build_service(monkeypatch)
    session = run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00",
    )))
    run(service.delete_session(USER, session["id"]))
    assert session["id"] not in att_repo.docs


def test_delete_session_other_user_is_noop(monkeypatch):
    service, att_repo, _, _, _ = build_service(monkeypatch)
    session = run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00",
    )))
    run(service.delete_session(OTHER_USER, session["id"]))
    assert session["id"] in att_repo.docs


# ---------- calendar (ore lavorate per dipendente/giorno) ----------

def test_calendar_aggrega_le_ore_dello_stesso_giorno(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-05T08:00:00+00:00", clock_out="2026-08-05T12:00:00+00:00",
    )))
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-05T13:00:00+00:00", clock_out="2026-08-05T17:00:00+00:00",
    )))

    rows = run(service.calendar(USER, "2026-08"))

    assert rows == [{"employee_id": "emp-1", "date": "2026-08-05", "hours": 8.0}]


def test_calendar_esclude_mesi_diversi(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-07-31T08:00:00+00:00", clock_out="2026-07-31T12:00:00+00:00",
    )))

    assert run(service.calendar(USER, "2026-08")) == []


def test_calendar_esclude_sessioni_ancora_aperte(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))

    assert run(service.calendar(USER, "2026-08")) == []


def test_calendar_scoped_per_utente(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": OTHER_USER["id"], "name": "Anna", "active": True, "pin_hash": None}
    run(service.create_manual_session(OTHER_USER, "emp-2", AttendanceCorrectionIn(
        clock_in="2026-08-05T08:00:00+00:00", clock_out="2026-08-05T12:00:00+00:00",
    )))

    assert run(service.calendar(USER, "2026-08")) == []


# ---------- export_csv (cartellino: presenze + assenze approvate) ----------

def test_export_csv_include_una_riga_per_sessione_chiusa(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-05T08:00:00+00:00", clock_out="2026-08-05T12:00:00+00:00", note="turno mattina",
    )))

    response = run(service.export_csv(USER, "2026-08"))
    rows = _rows_from_response(response)

    assert rows[0] == ["employee_name", "type", "date", "date_to", "clock_in", "clock_out", "hours", "note"]
    assert rows[1] == ["Mario Rossi", "Presenza", "2026-08-05", "", "10:00", "14:00", "4.0", "turno mattina"]


def test_export_csv_esclude_mesi_diversi(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-07-31T08:00:00+00:00", clock_out="2026-07-31T12:00:00+00:00",
    )))

    response = run(service.export_csv(USER, "2026-08"))
    rows = _rows_from_response(response)

    assert rows == [["employee_name", "type", "date", "date_to", "clock_in", "clock_out", "hours", "note"]]


def test_export_csv_esclude_sessioni_ancora_aperte(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))

    response = run(service.export_csv(USER, "2026-08"))
    rows = _rows_from_response(response)

    assert rows == [["employee_name", "type", "date", "date_to", "clock_in", "clock_out", "hours", "note"]]


def test_export_csv_include_assenze_approvate_del_mese(monkeypatch):
    service, _, _, _, leave_repo = build_service(monkeypatch)
    leave_repo.docs.append({
        "user_id": USER["id"], "employee_name": "Mario Rossi", "type": "ferie",
        "date_from": "2026-08-10", "date_to": "2026-08-12", "status": "approvata",
        "note": "ferie estive", "hours": None,
    })

    response = run(service.export_csv(USER, "2026-08"))
    rows = _rows_from_response(response)

    assert rows[1] == ["Mario Rossi", "Ferie", "2026-08-10", "2026-08-12", "", "", "", "ferie estive"]


def test_export_csv_esclude_assenze_non_approvate(monkeypatch):
    service, _, _, _, leave_repo = build_service(monkeypatch)
    leave_repo.docs.append({
        "user_id": USER["id"], "employee_name": "Mario Rossi", "type": "ferie",
        "date_from": "2026-08-10", "date_to": "2026-08-12", "status": "in_attesa",
        "note": "", "hours": None,
    })

    response = run(service.export_csv(USER, "2026-08"))
    rows = _rows_from_response(response)

    assert rows == [["employee_name", "type", "date", "date_to", "clock_in", "clock_out", "hours", "note"]]


def test_export_csv_scoped_per_utente(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": OTHER_USER["id"], "name": "Anna", "active": True, "pin_hash": None}
    run(service.create_manual_session(OTHER_USER, "emp-2", AttendanceCorrectionIn(
        clock_in="2026-08-05T08:00:00+00:00", clock_out="2026-08-05T12:00:00+00:00",
    )))

    response = run(service.export_csv(USER, "2026-08"))
    rows = _rows_from_response(response)

    assert rows == [["employee_name", "type", "date", "date_to", "clock_in", "clock_out", "hours", "note"]]


def test_export_csv_rispetta_il_rate_limit(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)

    import services.attendance_service as attendance_mod
    async def _always_blocked(*a, **kw):
        return False
    monkeypatch.setattr(attendance_mod, "check_and_record", _always_blocked)

    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        run(service.export_csv(USER, "2026-08"))


# ---------- AttendanceCorrectionIn: validazione intervallo ----------

def test_attendance_correction_in_rifiuta_uscita_prima_dellingresso():
    with pytest.raises(ValidationError, match="successiva"):
        AttendanceCorrectionIn(clock_in="2026-08-01T17:00:00+00:00", clock_out="2026-08-01T08:00:00+00:00")


def test_attendance_correction_in_rifiuta_uscita_uguale_allingresso():
    with pytest.raises(ValidationError, match="successiva"):
        AttendanceCorrectionIn(clock_in="2026-08-01T08:00:00+00:00", clock_out="2026-08-01T08:00:00+00:00")


def test_attendance_correction_in_accetta_senza_clock_out():
    corr = AttendanceCorrectionIn(clock_in="2026-08-01T08:00:00+00:00")
    assert corr.clock_out is None


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
