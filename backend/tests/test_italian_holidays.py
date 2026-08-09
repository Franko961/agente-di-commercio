"""
Verifica core/italian_holidays.py: usato solo dal conteggio ferie
"festivita" (vedi services/leave_request_service.py e
test_personale_module.py per l'uso end-to-end).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_italian_holidays.py -v
"""
import sys
from datetime import date

sys.path.insert(0, ".")

from core.italian_holidays import easter_sunday, is_italian_holiday


def test_easter_sunday_date_note_pubblicamente():
    assert easter_sunday(2024) == date(2024, 3, 31)
    assert easter_sunday(2025) == date(2025, 4, 20)
    assert easter_sunday(2026) == date(2026, 4, 5)
    assert easter_sunday(2027) == date(2027, 3, 28)


def test_is_italian_holiday_riconosce_le_feste_fisse():
    assert is_italian_holiday(date(2026, 1, 1))    # Capodanno
    assert is_italian_holiday(date(2026, 8, 15))   # Ferragosto
    assert is_italian_holiday(date(2026, 12, 25))  # Natale
    assert is_italian_holiday(date(2026, 12, 26))  # Santo Stefano


def test_is_italian_holiday_riconosce_pasquetta():
    assert is_italian_holiday(date(2026, 4, 6))    # lunedì dopo Pasqua 2026
    assert not is_italian_holiday(date(2026, 4, 5))  # la domenica di Pasqua stessa non è nella lista


def test_is_italian_holiday_falso_per_un_giorno_qualunque():
    assert not is_italian_holiday(date(2026, 8, 14))
    assert not is_italian_holiday(date(2026, 8, 19))  # sabato qualunque
