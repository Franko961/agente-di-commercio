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

from services.fiscal_calc import (
    compute_enasarco_con_massimale,
    compute_fiscal_breakdown,
)


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


def test_enasarco_massimale_sotto_soglia_nessun_effetto():
    # Ben sotto il massimale plurimandatario (30.478€): l'intero periodo è
    # imponibile, stesso risultato della formula piatta.
    result = compute_enasarco_con_massimale(0, 1000, esclusiva=False)
    assert result["imponibile"] == 1000.0
    assert result["contributo_enasarco"] == 85.0
    assert result["supera_massimale"] is False
    assert result["sotto_minimale"] is False


def test_enasarco_massimale_plurimandatario_taglia_la_quota_eccedente():
    # Già maturati 30.000€ quest'anno con questo mandante (plurimandatario,
    # massimale 30.478€): solo 478€ del nuovo periodo restano imponibili.
    result = compute_enasarco_con_massimale(30000, 2000, esclusiva=False)
    assert result["imponibile"] == 478.0
    assert result["contributo_enasarco"] == round(478.0 * 0.085, 2)
    assert result["supera_massimale"] is True


def test_enasarco_massimale_monomandatario_soglia_piu_alta():
    # Stesso cumulato di 30.000€, ma esclusiva=True: soglia 45.717€, non
    # ancora superata, quindi l'intero periodo resta imponibile.
    result = compute_enasarco_con_massimale(30000, 2000, esclusiva=True)
    assert result["imponibile"] == 2000.0
    assert result["supera_massimale"] is False


def test_enasarco_massimale_gia_superato_prima_del_periodo():
    # Il massimale era già superato PRIMA di questo periodo: nessuna parte
    # del nuovo lordo è più imponibile.
    result = compute_enasarco_con_massimale(35000, 1000, esclusiva=False)
    assert result["imponibile"] == 0.0
    assert result["contributo_enasarco"] == 0.0
    assert result["supera_massimale"] is True


def test_enasarco_sotto_minimale():
    result = compute_enasarco_con_massimale(0, 300, esclusiva=False)
    assert result["sotto_minimale"] is True
    assert result["supera_massimale"] is False
