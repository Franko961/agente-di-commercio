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
import openpyxl
from pydantic import ValidationError

sys.path.insert(0, ".")

from core.exceptions import NotFoundError, ValidationAppError, ConflictError
from core.security import hash_password
from core.utils import LOCAL_TZ
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


def _dettaglio_rows_from_response(response):
    """Consuma lo StreamingResponse di xlsx_response (export_xlsx) e
    ritorna le righe del foglio "Dettaglio" (stessa struttura piatta del
    precedente export CSV) come liste, per riusare gli stessi confronti
    di prima nei test sotto."""
    async def _collect():
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        return chunks
    chunks = asyncio.run(_collect())
    content = b"".join(c if isinstance(c, bytes) else c.encode() for c in chunks)
    wb = openpyxl.load_workbook(io.BytesIO(content))
    ws = wb["Dettaglio"]
    rows = []
    for row in ws.iter_rows(values_only=True):
        if all(v is None for v in row):
            continue
        rows.append(["" if v is None else str(v) for v in row])
    return rows


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

    async def find_clocked_in_between(self, user_id, start_iso, end_iso):
        # Stessa semantica del $gte/$lt su stringa ISO usato dal vero
        # AttendanceRepository.find_clocked_in_between (le stringhe ISO UTC
        # in questo formato ordinano correttamente anche come stringhe).
        return list({
            d["employee_id"] for d in self.docs.values()
            if d["user_id"] == user_id and start_iso <= d["clock_in"] < end_iso
        })

    async def insert(self, doc):
        # Simula l'indice parziale univoco MongoDB su (employee_id,
        # user_id) con clock_out=null (vedi startup_service.run_startup e
        # attendance_repository.insert): al massimo una sessione aperta
        # per dipendente, indipendentemente da cosa abbia visto
        # find_open_session() poco prima.
        if doc.get("clock_out") is None:
            for d in self.docs.values():
                if d["employee_id"] == doc["employee_id"] and d["user_id"] == doc["user_id"] and d["clock_out"] is None:
                    raise ConflictError("Sei già in servizio: registra prima l'uscita")
        self.docs[doc["id"]] = dict(doc)
        return doc

    async def update(self, sid, user_id, employee_id, data):
        d = self.docs.get(sid)
        if not d or d["user_id"] != user_id or d["employee_id"] != employee_id:
            return False
        d.update(data)
        return True

    async def delete(self, sid, user_id, employee_id):
        d = self.docs.get(sid)
        if d and d["user_id"] == user_id and d["employee_id"] == employee_id:
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
        "employment_status": "attivo",
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


def test_clock_in_kiosk_indice_univoco_blocca_la_race_condition(monkeypatch):
    """find_open_session() poi insert() non è atomico da solo: due
    timbrature d'ingresso simultanee potrebbero entrambe superare il
    pre-check prima che la prima abbia scritto. Qui si simula esattamente
    questa finestra (il pre-check non vede ancora la sessione aperta) e si
    verifica che l'ultima linea di difesa — l'indice parziale univoco
    MongoDB, simulato da FakeAttendanceRepo.insert — blocchi comunque il
    doppione con ConflictError, non con una seconda sessione aperta."""
    service, att_repo, _, _, _ = build_service(monkeypatch)
    run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))

    async def fake_find_open_session(employee_id, user_id):
        return None  # simula la finestra di race: il pre-check non vede la sessione già aperta

    monkeypatch.setattr(att_repo, "find_open_session", fake_find_open_session)

    with pytest.raises(ConflictError, match="già in servizio"):
        run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))

    # Una sola sessione aperta è davvero rimasta, non due.
    open_sessions = [d for d in att_repo.docs.values() if d["employee_id"] == "emp-1" and d["clock_out"] is None]
    assert len(open_sessions) == 1


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

    run(service.correct_session(USER, "emp-1", session["id"], AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00", clock_out="2026-08-01T17:00:00+00:00", note="orario corretto",
    )))

    updated = att_repo.docs[session["id"]]
    assert updated["clock_in"] == "2026-08-01T08:00:00+00:00"
    assert updated["clock_out"] == "2026-08-01T17:00:00+00:00"
    assert updated["corrected_by_admin"] is True


def test_correct_session_unknown_raises_404(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    with pytest.raises(NotFoundError):
        run(service.correct_session(USER, "emp-1", "does-not-exist", AttendanceCorrectionIn(
            clock_in="2026-08-01T08:00:00+00:00",
        )))


def test_correct_session_rifiuta_se_leid_nellurl_non_e_il_vero_proprietario(monkeypatch):
    """/employees/{eid}/attendance/{sid} con un sid che appartiene a un
    ALTRO dipendente dello stesso utente: non deve modificare la sessione
    solo perché sid+user_id combaciano, il percorso non corrisponde alla
    risorsa reale."""
    service, att_repo, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca", "active": True, "pin_hash": None}
    session = run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00",
    )))

    with pytest.raises(NotFoundError):
        run(service.correct_session(USER, "emp-2", session["id"], AttendanceCorrectionIn(
            clock_in="2026-08-02T08:00:00+00:00",
        )))

    # La sessione di emp-1 non deve essere stata toccata.
    assert att_repo.docs[session["id"]]["clock_in"] == "2026-08-01T08:00:00+00:00"


def test_delete_session_removes_it(monkeypatch):
    service, att_repo, _, _, _ = build_service(monkeypatch)
    session = run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00",
    )))
    run(service.delete_session(USER, "emp-1", session["id"]))
    assert session["id"] not in att_repo.docs


def test_delete_session_other_user_is_noop(monkeypatch):
    service, att_repo, _, _, _ = build_service(monkeypatch)
    session = run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00",
    )))
    run(service.delete_session(OTHER_USER, "emp-1", session["id"]))
    assert session["id"] in att_repo.docs


def test_delete_session_rifiuta_se_leid_nellurl_non_e_il_vero_proprietario(monkeypatch):
    service, att_repo, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": USER["id"], "name": "Luca", "active": True, "pin_hash": None}
    session = run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-01T08:00:00+00:00",
    )))

    run(service.delete_session(USER, "emp-2", session["id"]))

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


# ---------- expected_hours (ore attese da orario contrattuale) ----------

def test_expected_hours_dipendente_con_orario_completo(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00", "shift_end_time": "17:00"})

    rows = run(service.expected_hours(USER, "2026-08"))

    # Agosto 2026: 21 giorni feriali (lun-ven), 8h di turno ciascuno.
    assert len(rows) == 21
    assert all(r["employee_id"] == "emp-1" and r["hours"] == 8.0 for r in rows)
    assert {"employee_id": "emp-1", "date": "2026-08-03", "hours": 8.0} in rows  # lunedì
    assert not any(r["date"] == "2026-08-01" for r in rows)  # sabato: non lavorativo


def test_expected_hours_calcola_la_durata_del_turno(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0], "shift_start_time": "09:30", "shift_end_time": "13:00"})

    rows = run(service.expected_hours(USER, "2026-08"))

    assert all(r["hours"] == 3.5 for r in rows)


def test_expected_hours_sottrae_la_pausa_non_retribuita(monkeypatch):
    """Il caso che ha motivato il fix: 09:00-18:00 con un'ora di pausa
    pranzo deve dare 8 ore attese, non 9."""
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({
        "work_days": [0], "shift_start_time": "09:00", "shift_end_time": "18:00", "unpaid_break_minutes": 60,
    })

    rows = run(service.expected_hours(USER, "2026-08"))

    assert all(r["hours"] == 8.0 for r in rows)


def test_expected_hours_senza_pausa_configurata_non_sottrae_nulla(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0], "shift_start_time": "09:00", "shift_end_time": "18:00"})

    rows = run(service.expected_hours(USER, "2026-08"))

    assert all(r["hours"] == 9.0 for r in rows)


def test_expected_hours_esclude_dipendente_senza_fine_turno(monkeypatch):
    """shift_end_time è facoltativo su models.employee (a differenza di
    work_days/shift_start_time): un dipendente che ha configurato solo
    l'avviso di timbratura mancante (niente fine turno) non compare qui,
    niente riga invece di un valore a zero."""
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00"})

    assert run(service.expected_hours(USER, "2026-08")) == []


def test_expected_hours_esclude_dipendente_senza_orario(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    assert run(service.expected_hours(USER, "2026-08")) == []


def test_expected_hours_esclude_dipendente_non_attivo(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({
        "work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00", "shift_end_time": "17:00", "active": False,
    })

    assert run(service.expected_hours(USER, "2026-08")) == []


def test_expected_hours_esclude_dipendente_cessato(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({
        "work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00", "shift_end_time": "17:00",
        "employment_status": "cessato",
    })

    assert run(service.expected_hours(USER, "2026-08")) == []


def test_expected_hours_conta_solo_i_giorni_lavorativi_selezionati(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [5, 6], "shift_start_time": "10:00", "shift_end_time": "14:00"})

    rows = run(service.expected_hours(USER, "2026-08"))

    # Agosto 2026: 10 giorni di weekend (sabato+domenica).
    assert len(rows) == 10
    assert all(r["hours"] == 4.0 for r in rows)


def test_expected_hours_scoped_per_utente(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-2"] = {
        "id": "emp-2", "user_id": OTHER_USER["id"], "name": "Anna", "active": True, "pin_hash": None,
        "work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00", "shift_end_time": "17:00",
    }

    assert run(service.expected_hours(USER, "2026-08")) == []


def test_expected_hours_esclude_giorno_con_assenza_approvata(monkeypatch):
    service, _, emp_repo, _, leave_repo = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00", "shift_end_time": "17:00"})
    leave_repo.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "type": "ferie",
        "date_from": "2026-08-03", "date_to": "2026-08-03", "status": "approvata",
    })

    rows = run(service.expected_hours(USER, "2026-08"))

    assert not any(r["date"] == "2026-08-03" for r in rows)  # lunedì in ferie: nessuna riga
    assert any(r["date"] == "2026-08-04" for r in rows)  # martedì, non coperto: riga normale


def test_expected_hours_esclude_tutti_i_giorni_lavorativi_coperti_dallassenza(monkeypatch):
    service, _, emp_repo, _, leave_repo = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00", "shift_end_time": "17:00"})
    leave_repo.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "type": "malattia",
        "date_from": "2026-08-03", "date_to": "2026-08-07", "status": "approvata",
    })

    rows = run(service.expected_hours(USER, "2026-08"))

    settimana_in_malattia = {"2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07"}
    assert not any(r["date"] in settimana_in_malattia for r in rows)
    assert any(r["date"] == "2026-08-10" for r in rows)  # lunedì successivo, non coperto


def test_expected_hours_non_esclude_assenza_in_attesa(monkeypatch):
    """Solo le assenze APPROVATE tolgono ore attese — una richiesta ancora
    in attesa di decisione non ne ha ancora diritto, stesso principio già
    applicato ad automation_engine._eval_attendance_missing."""
    service, _, emp_repo, _, leave_repo = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00", "shift_end_time": "17:00"})
    leave_repo.docs.append({
        "user_id": USER["id"], "employee_id": "emp-1", "type": "ferie",
        "date_from": "2026-08-03", "date_to": "2026-08-03", "status": "in_attesa",
    })

    rows = run(service.expected_hours(USER, "2026-08"))

    assert any(r["date"] == "2026-08-03" for r in rows)


def test_expected_hours_assenza_di_un_altro_dipendente_non_influisce(monkeypatch):
    service, _, emp_repo, _, leave_repo = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00", "shift_end_time": "17:00"})
    leave_repo.docs.append({
        "user_id": USER["id"], "employee_id": "emp-2", "type": "ferie",
        "date_from": "2026-08-03", "date_to": "2026-08-03", "status": "approvata",
    })

    rows = run(service.expected_hours(USER, "2026-08"))

    assert any(r["date"] == "2026-08-03" for r in rows)


# ---------- today_summary (widget "Presenze oggi" della Dashboard) ----------

def test_today_summary_dipendente_atteso_e_gia_timbrato(monkeypatch):
    import services.attendance_service as attendance_mod
    from datetime import datetime as real_datetime

    monkeypatch.setattr(attendance_mod, "now_local", lambda: real_datetime(2026, 8, 3, 10, 0, tzinfo=LOCAL_TZ))  # lunedì

    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00"})
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-03T08:00:00+00:00", clock_out="2026-08-03T09:00:00+00:00",
    )))

    summary = run(service.today_summary(USER))

    assert summary == {"total_active": 1, "expected_today": 1, "clocked_today": 1}


def test_today_summary_dipendente_atteso_non_ancora_timbrato(monkeypatch):
    import services.attendance_service as attendance_mod
    from datetime import datetime as real_datetime

    monkeypatch.setattr(attendance_mod, "now_local", lambda: real_datetime(2026, 8, 3, 10, 0, tzinfo=LOCAL_TZ))

    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00"})

    summary = run(service.today_summary(USER))

    assert summary == {"total_active": 1, "expected_today": 1, "clocked_today": 0}


def test_today_summary_dipendente_senza_orario_non_e_atteso(monkeypatch):
    """Un dipendente senza work_days/shift_start_time conta nel totale
    attivi ma non tra gli attesi oggi: stesso criterio del trigger
    attendance_missing, niente falsi allarmi per chi non ha mai avuto un
    orario da rispettare."""
    import services.attendance_service as attendance_mod
    from datetime import datetime as real_datetime

    monkeypatch.setattr(attendance_mod, "now_local", lambda: real_datetime(2026, 8, 3, 10, 0, tzinfo=LOCAL_TZ))

    service, _, _, _, _ = build_service(monkeypatch)

    summary = run(service.today_summary(USER))

    assert summary == {"total_active": 1, "expected_today": 0, "clocked_today": 0}


def test_today_summary_giorno_non_lavorativo_non_e_atteso(monkeypatch):
    import services.attendance_service as attendance_mod
    from datetime import datetime as real_datetime

    monkeypatch.setattr(attendance_mod, "now_local", lambda: real_datetime(2026, 8, 3, 10, 0, tzinfo=LOCAL_TZ))  # lunedì

    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [5, 6], "shift_start_time": "09:00"})  # solo weekend

    summary = run(service.today_summary(USER))

    assert summary == {"total_active": 1, "expected_today": 0, "clocked_today": 0}


def test_today_summary_dipendente_non_attivo_escluso(monkeypatch):
    import services.attendance_service as attendance_mod
    from datetime import datetime as real_datetime

    monkeypatch.setattr(attendance_mod, "now_local", lambda: real_datetime(2026, 8, 3, 10, 0, tzinfo=LOCAL_TZ))

    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00", "active": False})

    summary = run(service.today_summary(USER))

    assert summary == {"total_active": 0, "expected_today": 0, "clocked_today": 0}


def test_today_summary_scoped_per_utente(monkeypatch):
    import services.attendance_service as attendance_mod
    from datetime import datetime as real_datetime

    monkeypatch.setattr(attendance_mod, "now_local", lambda: real_datetime(2026, 8, 3, 10, 0, tzinfo=LOCAL_TZ))

    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-2"] = {
        "id": "emp-2", "user_id": OTHER_USER["id"], "name": "Anna", "active": True, "pin_hash": None,
        "work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00",
    }

    summary = run(service.today_summary(USER))

    assert summary == {"total_active": 1, "expected_today": 0, "clocked_today": 0}


def test_today_summary_confine_del_giorno_in_ora_italiana(monkeypatch):
    """Il calcolo di 'oggi' passa dal confine di mezzanotte in ora
    italiana (CEST, UTC+2 il 3 agosto), non da mezzanotte UTC: una
    timbratura delle 23:59 locali di ieri (21:59 UTC) NON deve contare
    come di oggi, una delle 00:00 locali di oggi (22:00 UTC di ieri) sì."""
    import services.attendance_service as attendance_mod
    from datetime import datetime as real_datetime

    monkeypatch.setattr(attendance_mod, "now_local", lambda: real_datetime(2026, 8, 3, 10, 0, tzinfo=LOCAL_TZ))

    service, att_repo, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-1"].update({"work_days": [0, 1, 2, 3, 4], "shift_start_time": "09:00"})
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-02T21:59:00+00:00", clock_out="2026-08-02T22:30:00+00:00",  # 23:59 di ieri in ora italiana
    )))

    summary_ieri_tardi = run(service.today_summary(USER))
    assert summary_ieri_tardi["clocked_today"] == 0

    del att_repo.docs[list(att_repo.docs.keys())[0]]
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-02T22:00:00+00:00", clock_out="2026-08-02T22:30:00+00:00",  # 00:00 di oggi in ora italiana
    )))

    summary_oggi_presto = run(service.today_summary(USER))
    assert summary_oggi_presto["clocked_today"] == 1


# ---------- export_xlsx (cartellino: presenze + assenze approvate) ----------
# Il foglio "Dettaglio" (vedi attendance_xlsx_export.py) mantiene la stessa
# struttura piatta del precedente export CSV, solo con intestazioni in
# italiano — questi test riusano gli stessi scenari già coperti prima.

_DETTAGLIO_HEADER = ["Dipendente", "Tipo", "Data", "Data fine", "Entrata", "Uscita", "Ore", "Note"]


def test_export_xlsx_include_una_riga_per_sessione_chiusa(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-08-05T08:00:00+00:00", clock_out="2026-08-05T12:00:00+00:00", note="turno mattina",
    )))

    response = run(service.export_xlsx(USER, "2026-08"))
    rows = _dettaglio_rows_from_response(response)

    assert rows[0] == _DETTAGLIO_HEADER
    # Un numero "intero" (4.0 ore) viene riletto come "4" dopo il giro di
    # boa xlsx: il formato non distingue int/float per un valore senza
    # decimali, a differenza del CSV — non è una perdita di precisione.
    assert rows[1] == ["Mario Rossi", "Presenza", "2026-08-05", "", "10:00", "14:00", "4", "turno mattina"]


def test_export_xlsx_esclude_mesi_diversi(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    run(service.create_manual_session(USER, "emp-1", AttendanceCorrectionIn(
        clock_in="2026-07-31T08:00:00+00:00", clock_out="2026-07-31T12:00:00+00:00",
    )))

    response = run(service.export_xlsx(USER, "2026-08"))
    rows = _dettaglio_rows_from_response(response)

    assert rows == [_DETTAGLIO_HEADER]


def test_export_xlsx_esclude_sessioni_ancora_aperte(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)
    run(service.clock_in_kiosk(KIOSK_TOKEN, "emp-1", PIN))

    response = run(service.export_xlsx(USER, "2026-08"))
    rows = _dettaglio_rows_from_response(response)

    assert rows == [_DETTAGLIO_HEADER]


def test_export_xlsx_include_assenze_approvate_del_mese(monkeypatch):
    service, _, _, _, leave_repo = build_service(monkeypatch)
    leave_repo.docs.append({
        "user_id": USER["id"], "employee_name": "Mario Rossi", "type": "ferie",
        "date_from": "2026-08-10", "date_to": "2026-08-12", "status": "approvata",
        "note": "ferie estive", "hours": None,
    })

    response = run(service.export_xlsx(USER, "2026-08"))
    rows = _dettaglio_rows_from_response(response)

    assert rows[1] == ["Mario Rossi", "Ferie", "2026-08-10", "2026-08-12", "", "", "", "ferie estive"]


def test_export_xlsx_ritaglia_lassenza_a_cavallo_tra_due_mesi(monkeypatch):
    """Un'assenza che attraversa il confine del mese (28 luglio - 5 agosto)
    deve comparire nel cartellino di agosto solo con la porzione di agosto
    (1-5), non con l'intervallo originale — altrimenti il cartellino di
    luglio E quello di agosto mostrerebbero entrambi l'intero intervallo,
    facendo tornare male qualunque conteggio giorni per mese."""
    service, _, _, _, leave_repo = build_service(monkeypatch)
    leave_repo.docs.append({
        "user_id": USER["id"], "employee_name": "Mario Rossi", "type": "ferie",
        "date_from": "2026-07-28", "date_to": "2026-08-05", "status": "approvata",
        "note": "", "hours": None,
    })

    response = run(service.export_xlsx(USER, "2026-08"))
    rows = _dettaglio_rows_from_response(response)

    assert rows[1] == ["Mario Rossi", "Ferie", "2026-08-01", "2026-08-05", "", "", "", ""]


def test_export_xlsx_ritaglia_lassenza_che_finisce_nel_mese_successivo(monkeypatch):
    service, _, _, _, leave_repo = build_service(monkeypatch)
    leave_repo.docs.append({
        "user_id": USER["id"], "employee_name": "Mario Rossi", "type": "malattia",
        "date_from": "2026-08-28", "date_to": "2026-09-03", "status": "approvata",
        "note": "", "hours": None,
    })

    response = run(service.export_xlsx(USER, "2026-08"))
    rows = _dettaglio_rows_from_response(response)

    assert rows[1] == ["Mario Rossi", "Malattia", "2026-08-28", "2026-08-31", "", "", "", ""]


def test_export_xlsx_esclude_assenze_non_approvate(monkeypatch):
    service, _, _, _, leave_repo = build_service(monkeypatch)
    leave_repo.docs.append({
        "user_id": USER["id"], "employee_name": "Mario Rossi", "type": "ferie",
        "date_from": "2026-08-10", "date_to": "2026-08-12", "status": "in_attesa",
        "note": "", "hours": None,
    })

    response = run(service.export_xlsx(USER, "2026-08"))
    rows = _dettaglio_rows_from_response(response)

    assert rows == [_DETTAGLIO_HEADER]


def test_export_xlsx_scoped_per_utente(monkeypatch):
    service, _, emp_repo, _, _ = build_service(monkeypatch)
    emp_repo.docs["emp-2"] = {"id": "emp-2", "user_id": OTHER_USER["id"], "name": "Anna", "active": True, "pin_hash": None}
    run(service.create_manual_session(OTHER_USER, "emp-2", AttendanceCorrectionIn(
        clock_in="2026-08-05T08:00:00+00:00", clock_out="2026-08-05T12:00:00+00:00",
    )))

    response = run(service.export_xlsx(USER, "2026-08"))
    rows = _dettaglio_rows_from_response(response)

    assert rows == [_DETTAGLIO_HEADER]


def test_export_xlsx_rispetta_il_rate_limit(monkeypatch):
    service, _, _, _, _ = build_service(monkeypatch)

    import services.attendance_service as attendance_mod
    async def _always_blocked(*a, **kw):
        return False
    monkeypatch.setattr(attendance_mod, "check_and_record", _always_blocked)

    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        run(service.export_xlsx(USER, "2026-08"))


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


def test_attendance_correction_in_rifiuta_clock_in_malformato_senza_clock_out():
    """Il bug che ha motivato il fix: prima il validatore controllava il
    formato di clock_in SOLO se clock_out era presente, quindi una
    sessione manuale ancora aperta poteva passare con un clock_in non
    parsabile — che avrebbe poi rotto silenziosamente calendario/export
    nel momento in cui la sessione veniva chiusa."""
    with pytest.raises(ValidationError, match="ingresso non valido"):
        AttendanceCorrectionIn(clock_in="pippo")


def test_attendance_correction_in_rifiuta_clock_in_malformato_con_clock_out():
    with pytest.raises(ValidationError, match="ingresso non valido"):
        AttendanceCorrectionIn(clock_in="pippo", clock_out="2026-08-01T17:00:00+00:00")


def test_attendance_correction_in_rifiuta_clock_out_malformato():
    with pytest.raises(ValidationError, match="uscita non valido"):
        AttendanceCorrectionIn(clock_in="2026-08-01T08:00:00+00:00", clock_out="pippo")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
