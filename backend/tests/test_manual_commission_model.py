"""
Verifica ManualCommissionIn: il modello del box "provvigioni inserite
manualmente" nella pagina Provvigioni — period deve essere un mese valido
("YYYY-MM"), amount non negativo e con lo stesso tetto massimo già usato
per gli altri importi economici di grande entità (MAX_MONETARY_TARGET,
vedi core/validation_limits.py).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_manual_commission_model.py -v
"""
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, ".")

from core.validation_limits import MAX_MONETARY_TARGET
from models.commission import ManualCommissionIn


def test_valore_valido_accettato():
    m = ManualCommissionIn(period="2026-08", amount=450.50)
    assert m.period == "2026-08"
    assert m.amount == 450.50


def test_amount_zero_accettato():
    """Zero è un valore legittimo (es. per 'azzerare' il mese senza
    cancellare la riga)."""
    m = ManualCommissionIn(period="2026-08", amount=0)
    assert m.amount == 0


def test_amount_negativo_rifiutato():
    with pytest.raises(ValidationError):
        ManualCommissionIn(period="2026-08", amount=-1)


def test_amount_oltre_il_limite_rifiutato():
    with pytest.raises(ValidationError):
        ManualCommissionIn(period="2026-08", amount=MAX_MONETARY_TARGET + 1)


@pytest.mark.parametrize("period", ["2026-13", "2026-00", "26-08", "2026/08", "agosto-2026", "2026-8", ""])
def test_period_malformato_rifiutato(period):
    with pytest.raises(ValidationError):
        ManualCommissionIn(period=period, amount=100)


@pytest.mark.parametrize("period", ["2026-01", "2026-08", "2026-12", "2099-12"])
def test_period_valido_accettato(period):
    m = ManualCommissionIn(period=period, amount=100)
    assert m.period == period


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
