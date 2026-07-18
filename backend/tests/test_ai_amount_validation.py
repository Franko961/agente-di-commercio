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


# ---------- prepare_add_expense ----------

def test_prepare_expense_rifiuta_importo_testuale():
    result = ai_service.prepare_add_expense({"category": "carburante", "amount": "quaranta"})
    assert "error" in result


def test_prepare_expense_rifiuta_importo_zero():
    result = ai_service.prepare_add_expense({"category": "carburante", "amount": 0})
    assert "error" in result


def test_prepare_expense_rifiuta_importo_negativo():
    result = ai_service.prepare_add_expense({"category": "carburante", "amount": -50})
    assert "error" in result


def test_prepare_expense_accetta_importo_valido():
    result = ai_service.prepare_add_expense({"category": "carburante", "amount": 45.5})
    assert "error" not in result
    assert result["resolved_input"]["amount"] == 45.5


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
    test_safe_float_su_valori_validi()
    test_safe_float_su_valori_non_validi_torna_il_default()
    test_prepare_expense_rifiuta_importo_testuale()
    test_prepare_expense_rifiuta_importo_zero()
    test_prepare_expense_rifiuta_importo_negativo()
    test_prepare_expense_accetta_importo_valido()
    test_finalize_expense_con_importo_malformato_non_scrive_e_non_esplode()
    test_execute_crm_tool_add_expense_con_importo_testuale_non_esplode()
    print("OK: tutti i test di validazione importi passati")
