"""
Test isolato (mock) per la validazione robusta di importi/quantità/prezzi nei
tool economici dell'AI (add_offer, add_expense). Verifica che un valore non
numerico, mancante, zero o negativo — che sia arrivato da una trascrizione
vocale imprecisa o da una risposta malformata del modello — non provochi mai
un'eccezione non gestita né scriva un record con importo non valido, ma
restituisca sempre un messaggio d'errore chiaro ("❌ ...").

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_amount_validation.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

from services.ai_service import ai_service, _safe_float


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------- _safe_float ----------

def test_safe_float_su_valori_validi():
    assert _safe_float("42") == 42.0
    assert _safe_float(3.14) == 3.14
    assert _safe_float(-5) == -5.0


def test_safe_float_su_valori_non_validi_torna_il_default():
    assert _safe_float("quaranta", 0) == 0
    assert _safe_float(None, 0) == 0
    assert _safe_float("", 0) == 0
    assert _safe_float("quaranta", 99) == 99


def test_safe_float_su_formato_italiano_con_virgola_decimale():
    assert _safe_float("45,90") == 45.90
    assert _safe_float("1500,5") == 1500.5


def test_safe_float_su_formato_italiano_con_migliaia_e_decimali():
    assert _safe_float("1.500,50") == 1500.50
    assert _safe_float("12.345,67") == 12345.67


def test_safe_float_rimuove_simbolo_euro_e_spazi():
    assert _safe_float("€ 120") == 120.0
    assert _safe_float("  € 45,00 ") == 45.0
    assert _safe_float("120 €") == 120.0


def test_safe_float_formato_anglosassone_resta_invariato():
    # Senza virgola non c'è modo di distinguere in modo affidabile un punto
    # decimale anglosassone da un separatore delle migliaia italiano: il
    # comportamento documentato è trattarlo come notazione anglosassone.
    assert _safe_float("45.90") == 45.90
    assert _safe_float(45.5) == 45.5


# ---------- prepare_add_expense ----------

def test_prepare_expense_rifiuta_importo_testuale():
    result = run(ai_service.prepare_add_expense({"category": "carburante", "amount": "quaranta"}, "u1"))
    assert "error" in result


def test_prepare_expense_rifiuta_importo_zero():
    result = run(ai_service.prepare_add_expense({"category": "carburante", "amount": 0}, "u1"))
    assert "error" in result


def test_prepare_expense_rifiuta_importo_negativo():
    result = run(ai_service.prepare_add_expense({"category": "carburante", "amount": -50}, "u1"))
    assert "error" in result


def test_prepare_expense_accetta_importo_valido():
    result = run(ai_service.prepare_add_expense({"category": "carburante", "amount": 45.5}, "u1"))
    assert "error" not in result
    assert result["resolved_input"]["amount"] == 45.5


def test_prepare_expense_accetta_importo_in_formato_italiano():
    """Caso reale: un importo dettato a voce o trascritto dal modello nel
    formato italiano ('45,90' invece di '45.9') non deve essere respinto
    come importo non valido."""
    result = run(ai_service.prepare_add_expense({"category": "carburante", "amount": "45,90"}, "u1"))
    assert "error" not in result
    assert result["resolved_input"]["amount"] == 45.90


# ---------- _finalize_expense (chiamato anche direttamente da /execute-action) ----------

def test_finalize_expense_con_importo_malformato_non_scrive_e_non_esplode():
    msg = asyncio.get_event_loop().run_until_complete(
        ai_service._finalize_expense("u1", {"category": "vitto", "amount": "abc", "date": "2026-07-17"})
    )
    assert msg.startswith("❌")


# ---------- execute_crm_tool (percorso diretto per spese sotto soglia) ----------

def test_execute_crm_tool_add_expense_con_importo_testuale_non_esplode():
    result = asyncio.get_event_loop().run_until_complete(
        ai_service.execute_crm_tool("add_expense", {"category": "vitto", "amount": "non è un numero"}, "u1")
    )
    assert result.startswith("❌")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
