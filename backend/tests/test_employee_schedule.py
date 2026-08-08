"""
Test per l'orario contrattuale del dipendente (work_days/shift_start_time,
vedi models/employee.py) — usato SOLO da
automation_engine._eval_attendance_missing per segnalare una timbratura
mancante (vedi tests/test_automation_engine.py per il trigger vero e
proprio). Qui si verifica solo la validazione del modello.

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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
