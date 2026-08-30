"""
Verifica services/fiscal_calc.py — calcolo ritenuta d'acconto e contributo
ENASARCO su una provvigione lorda reale. Le stesse aliquote sono verificate
(fact-check con fonti ufficiali) nell'articolo del blog "ritenuta d'acconto
e contributi ENASARCO" e nel suo calcolatore JS gemello
(frontend/src/utils/fiscalCalc.js) — questo test blocca una regressione
silenziosa se le due implementazioni divergessero.

Esegui con:
    python -m pytest tests/test_fiscal_calc.py -v
"""

import sys

sys.path.insert(0, ".")

from services.fiscal_calc import compute_fiscal_breakdown


def test_forfettario_nessuna_ritenuta():
    result = compute_fiscal_breakdown(1000, "forfettario", "50")
    assert result == {
        "lordo": 1000.0,
        "ritenuta_acconto": 0.0,
        "contributo_enasarco": 85.0,
        "netto": 915.0,
    }


def test_ordinario_base_standard_11_5_percento():
    result = compute_fiscal_breakdown(1000, "ordinario", "50")
    assert result["ritenuta_acconto"] == 115.0
    assert result["contributo_enasarco"] == 85.0
    assert result["netto"] == 800.0


def test_ordinario_base_ridotta_4_6_percento():
    result = compute_fiscal_breakdown(1000, "ordinario", "20")
    assert result["ritenuta_acconto"] == 46.0
    assert result["contributo_enasarco"] == 85.0
    assert result["netto"] == 869.0


def test_lordo_negativo_trattato_come_zero():
    result = compute_fiscal_breakdown(-50, "ordinario", "50")
    assert result == {
        "lordo": 0.0,
        "ritenuta_acconto": 0.0,
        "contributo_enasarco": 0.0,
        "netto": 0.0,
    }


def test_arrotondamento_a_due_decimali():
    result = compute_fiscal_breakdown(333.33, "ordinario", "50")
    assert result["ritenuta_acconto"] == round(333.33 * 0.5 * 0.23, 2)
    assert result["contributo_enasarco"] == round(333.33 * 0.085, 2)
