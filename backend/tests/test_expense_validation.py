"""
Verifica la validazione aggiunta a ExpenseIn (importo positivo, data
calendaristicamente valida): il percorso di creazione spesa via assistente
AI aveva già questi controlli (services.ai_service._safe_float /
_validate_expense_date), ma il form/API diretta (POST /api/expenses) no —
permetteva importi zero/negativi e date inesistenti, alterando i totali di
spesa mostrati in dashboard/report.

Esegui con:
    JWT_SECRET=test python -m pytest tests/test_expense_validation.py -v
"""

import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from models.expense import ExpenseIn


def _base(**overrides):
    payload = {"date": "2026-07-15", "amount": 50.0, **overrides}
    return payload


def test_spesa_valida_accettata():
    e = ExpenseIn(**_base())
    assert e.amount == 50.0
    assert e.date == "2026-07-15"


@pytest.mark.parametrize("amount", [0, -1, -50.5])
def test_importo_zero_o_negativo_rifiutato(amount):
    with pytest.raises(ValidationError):
        ExpenseIn(**_base(amount=amount))


@pytest.mark.parametrize(
    "date", ["2026-15-80", "non-una-data", "", "2026/07/15", "15-07-2026"]
)
def test_data_non_valida_rifiutata(date):
    with pytest.raises(ValidationError):
        ExpenseIn(**_base(date=date))


def test_data_calendaristicamente_inesistente_rifiutata():
    """31 novembre non esiste: sintatticamente simile a una data valida ma
    calendaristicamente impossibile — stesso controllo già applicato lato AI."""
    with pytest.raises(ValidationError):
        ExpenseIn(**_base(date="2026-11-31"))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
