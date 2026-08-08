"""
Verifica services/attendance_service.py: rilevazione presenze v1 (solo
timbratura ingresso/uscita con timestamp lato server, senza
geolocalizzazione — vedi il docstring della classe per il perché) tramite
il link personale del dipendente (stesso pattern pubblico di
leave_request_service.py), più la gestione lato responsabile
(elenco/inserimento manuale/correzione/eliminazione di una sessione).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_attendance_service.py -v
"""
import sys
import asyncio

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from core.exceptions import NotFoundError, ValidationAppError
from models.attendance import AttendanceCorrectionIn
from services.attendance_service import AttendanceService


def run(coro):
    return asyncio.run(coro)


USER = {"id": "user-1", "email": "manager@example.com", "enabled_extra_modules": ["personale"]}
OTHER_USER = {"id": "user-2", "email": "altro@example.com", "enabled_extra_modules": ["personale"]}
TOKEN = "il-token-del-dipendente"


class FakeEmployeeRepo:
    def __init__(self):
        self.docs = {}

    async def find_one(self, eid, user_id):
        d = self.docs.get(eid)
        return d if d and d["user_id"] == user_id else None

    async def find_by_token_hash(self, token_hash):
        for d in self.docs.values():
            if d.get("_token_hash") == token_hash:
                return d
        return None


class FakeUserRepo:
    def __init__(self):
        self.docs = {}

    async def find_by_id(self, uid):
        return self.docs.get(uid)


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


def build_service(monkeypatch=None):
    att_repo = FakeAttendanceRepo()
    emp_repo = FakeEmployeeRepo()
    emp_repo.docs["emp-1"] = {
        "id": "emp-1", "user_id": USER["id"], "name": "Mario", "surname": "Rossi",
        "active": True, "_token_hash": "hash-del-token",
    }
    user_repo = FakeUserRepo()
    user_repo.docs[USER["id"]] = USER
    user_repo.docs[OTHER_USER["id"]] = OTHER_USER
    service = AttendanceService(repo=att_repo, employees=emp_repo, users=user_repo)
    if monkeypatch:
        import services.attendance_service as attendance_mod
        monkeypatch.setattr(attendance_mod, "hash_reset_token", lambda t: "hash-del-token" if t == TOKEN else "altro")
        monkeypatch.setattr(attendance_mod, "check_and_record", _always_ok)
    return service, att_repo, emp_repo, user_repo


async def _always_ok(*args, **kwargs):
    return True


# ---------- clock_in / clock_out (pubblico via token) ----------

def test_clock_in_crea_una_sessione_aperta(monkeypatch):
    service, att_repo, _, _ = build_service(monkeypatch)
    session = run(service.clock_in(TOKEN))
    assert session["employee_id"] == "emp-1"
    assert session["clock_out"] is None
    assert session["corrected_by_admin"] is False
    assert session["clock_in"] is not None


def test_clock_in_rifiuta_se_gia_in_servizio(monkeypatch):
    service, att_repo, _, _ = build_service(monkeypatch)
    run(service.clock_in(TOKEN))
    with pytest.raises(ValidationAppError):
        run(service.clock_in(TOKEN))


def test_clock_out_chiude_la_sessione_aperta(monkeypatch):
    service, att_repo, _, _ = build_service(monkeypatch)
    session = run(service.clock_in(TOKEN))
    closed = run(service.clock_out(TOKEN))
    assert closed["id"] == session["id"]
    assert closed["clock_out"] is not None
    assert att_repo.docs[session["id"]]["clock_out"] is not None


def test_clock_out_rifiuta_se_nessuna_sessione_aperta(monkeypatch):
    service, att_repo, _, _ = build_service(monkeypatch)
    with pytest.raises(ValidationAppError):
        run(service.clock_out(TOKEN))


def test_clock_in_rifiuta_token_non_valido(monkeypatch):
    service, att_repo, _, _ = build_service(monkeypatch)
    with pytest.raises(NotFoundError):
        run(service.clock_in("token-sbagliato"))


def test_clock_in_rifiuta_se_dipendente_disattivato(monkeypatch):
    service, att_repo, emp_repo, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"]["active"] = False
    with pytest.raises(NotFoundError):
        run(service.clock_in(TOKEN))


def test_clock_in_rifiuta_se_modulo_personale_disattivato(monkeypatch):
    service, att_repo, _, user_repo = build_service(monkeypatch)
    user_repo.docs[USER["id"]] = {**USER, "enabled_extra_modules": []}
    with pytest.raises(NotFoundError):
        run(service.clock_in(TOKEN))


# ---------- status ----------

def test_status_riflette_la_sessione_aperta(monkeypatch):
    service, att_repo, _, _ = build_service(monkeypatch)
    before = run(service.status(TOKEN))
    assert before == {"clocked_in": False, "since": None}

    session = run(service.clock_in(TOKEN))
    during = run(service.status(TOKEN))
    assert during["clocked_in"] is True
    assert during["since"] == session["clock_in"]

    run(service.clock_out(TOKEN))
    after = run(service.status(TOKEN))
    assert after == {"clocked_in": False, "since": None}


# ---------- lato admin ----------

def test_list_sessions_scoped_a_dipendente_e_utente(monkeypatch):
    service, att_repo, emp_repo, _ = build_service(monkeypatch)
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca", "active": True}
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
    service, att_repo, _, _ = build_service(monkeypatch)
    session = run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00", clock_out="2026-08-01T17:00:00+00:00", note="dimenticato",
    )))
    assert session["corrected_by_admin"] is True
    assert session["note"] == "dimenticato"


def test_create_manual_session_rejects_unknown_employee(monkeypatch):
    service, _, _, _ = build_service(monkeypatch)
    with pytest.raises(ValidationAppError):
        run(service.create_manual_session(USER, "emp-does-not-exist", AttendanceCorrectionIn(
            clock_in="2026-08-01T08:00:00+00:00",
        )))


def test_correct_session_aggiorna_orari_e_marca_corretta(monkeypatch):
    service, att_repo, _, _ = build_service(monkeypatch)
    session = run(service.clock_in(TOKEN))

    run(service.correct_session(USER, session["id"], AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00", clock_out="2026-08-01T17:00:00+00:00", note="orario corretto",
    )))

    updated = att_repo.docs[session["id"]]
    assert updated["clock_in"] == "2026-08-01T08:00:00+00:00"
    assert updated["clock_out"] == "2026-08-01T17:00:00+00:00"
    assert updated["corrected_by_admin"] is True


def test_correct_session_unknown_raises_404(monkeypatch):
    service, _, _, _ = build_service(monkeypatch)
    with pytest.raises(NotFoundError):
        run(service.correct_session(USER, "does-not-exist", AttendanceCorrectionIn(
            clock_in="2026-08-01T08:00:00+00:00",
        )))


def test_delete_session_removes_it(monkeypatch):
    service, att_repo, _, _ = build_service(monkeypatch)
    session = run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00",
    )))
    run(service.delete_session(USER, session["id"]))
    assert session["id"] not in att_repo.docs


def test_delete_session_other_user_is_noop(monkeypatch):
    service, att_repo, _, _ = build_service(monkeypatch)
    session = run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00",
    )))
    run(service.delete_session(OTHER_USER, session["id"]))
    assert session["id"] in att_repo.docs


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
