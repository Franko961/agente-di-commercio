"""
Test per l'orario contrattuale del dipendente (work_days/shift_start_time/
shift_end_time, vedi models/employee.py) — work_days/shift_start_time usati
da automation_engine._eval_attendance_missing per segnalare una timbratura
mancante (vedi tests/test_automation_engine.py per il trigger vero e
proprio), shift_end_time usato da attendance_service.expected_hours per il
confronto ore attese/reali (vedi tests/test_attendance_service.py). Qui si
verifica solo la validazione del modello.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_employee_schedule.py -v
"""
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from models.employee import EmployeeIn


def _payload(**overrides):
    base = {"name": "Mario"}
    base.update(overrides)
    return base


def test_nessun_orario_impostato_e_valido():
    e = EmployeeIn(**_payload())
    assert e.work_days is None
    assert e.shift_start_time is None


def test_orario_completo_e_valido():
    e = EmployeeIn(**_payload(work_days=[0, 1, 2, 3, 4], shift_start_time="09:00"))
    assert e.work_days == [0, 1, 2, 3, 4]
    assert e.shift_start_time == "09:00"


def test_work_days_senza_shift_start_time_e_rifiutato():
    with pytest.raises(ValidationError, match="vanno impostati insieme"):
        EmployeeIn(**_payload(work_days=[0, 1, 2, 3, 4]))


def test_shift_start_time_senza_work_days_e_rifiutato():
    with pytest.raises(ValidationError, match="vanno impostati insieme"):
        EmployeeIn(**_payload(shift_start_time="09:00"))


def test_work_days_vuoto_e_rifiutato():
    with pytest.raises(ValidationError, match="almeno un giorno"):
        EmployeeIn(**_payload(work_days=[], shift_start_time="09:00"))


def test_work_day_fuori_range_e_rifiutato():
    with pytest.raises(ValidationError, match="Giorno lavorativo non valido"):
        EmployeeIn(**_payload(work_days=[0, 7], shift_start_time="09:00"))


def test_shift_start_time_malformato_e_rifiutato():
    with pytest.raises(ValidationError):
        EmployeeIn(**_payload(work_days=[0], shift_start_time="9:00"))


def test_shift_start_time_ora_invalida_e_rifiutato():
    with pytest.raises(ValidationError):
        EmployeeIn(**_payload(work_days=[0], shift_start_time="25:00"))


# ---------- shift_end_time ----------

def test_orario_con_fine_turno_e_valido():
    e = EmployeeIn(**_payload(work_days=[0], shift_start_time="09:00", shift_end_time="18:00"))
    assert e.shift_end_time == "18:00"


def test_solo_inizio_turno_senza_fine_e_valido():
    """A differenza di work_days/shift_start_time, shift_end_time NON è
    obbligatorio: un dipendente con solo l'inizio turno impostato (es. da
    prima che esistesse questo campo) resta valido — semplicemente non avrà
    il confronto ore attese/reali finché non si compila anche la fine."""
    e = EmployeeIn(**_payload(work_days=[0], shift_start_time="09:00"))
    assert e.shift_end_time is None


def test_fine_turno_senza_inizio_e_rifiutato():
    with pytest.raises(ValidationError, match="richiede anche l'orario di inizio"):
        EmployeeIn(**_payload(shift_end_time="18:00"))


def test_fine_turno_precedente_allinizio_e_rifiutato():
    with pytest.raises(ValidationError, match="deve essere successivo"):
        EmployeeIn(**_payload(work_days=[0], shift_start_time="18:00", shift_end_time="09:00"))


def test_fine_turno_uguale_allinizio_e_rifiutato():
    with pytest.raises(ValidationError, match="deve essere successivo"):
        EmployeeIn(**_payload(work_days=[0], shift_start_time="09:00", shift_end_time="09:00"))


# ---------- unpaid_break_minutes ----------

def test_pausa_di_default_e_zero():
    e = EmployeeIn(**_payload())
    assert e.unpaid_break_minutes == 0


def test_pausa_con_turno_completo_e_valida():
    e = EmployeeIn(**_payload(work_days=[0], shift_start_time="09:00", shift_end_time="18:00", unpaid_break_minutes=60))
    assert e.unpaid_break_minutes == 60


def test_pausa_senza_alcun_turno_e_valida():
    """Non richiede shift_end_time impostato: se non c'è un turno da cui
    sottrarla resta semplicemente inutilizzata, non un dato incoerente."""
    e = EmployeeIn(**_payload(unpaid_break_minutes=30))
    assert e.unpaid_break_minutes == 30


def test_pausa_uguale_alla_durata_del_turno_e_rifiutata():
    with pytest.raises(ValidationError, match="non può durare quanto o più dell'intero turno"):
        EmployeeIn(**_payload(work_days=[0], shift_start_time="09:00", shift_end_time="10:00", unpaid_break_minutes=60))


def test_pausa_maggiore_della_durata_del_turno_e_rifiutata():
    with pytest.raises(ValidationError, match="non può durare quanto o più dell'intero turno"):
        EmployeeIn(**_payload(work_days=[0], shift_start_time="09:00", shift_end_time="10:00", unpaid_break_minutes=90))


def test_pausa_negativa_e_rifiutata():
    with pytest.raises(ValidationError):
        EmployeeIn(**_payload(unpaid_break_minutes=-1))


def test_pausa_oltre_il_tetto_e_rifiutata():
    with pytest.raises(ValidationError):
        EmployeeIn(**_payload(unpaid_break_minutes=481))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
