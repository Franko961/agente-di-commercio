"""
Test isolato (mock) per la validazione della data di una spesa nei tool
economici dell'AI (add_expense). Prima di questa fix, `resolved.get("date")
or now_iso()[:10]` accettava qualunque valore non vuoto senza controllarne il
formato: una data come "2026-15-80" (mese/giorno inesistenti), "domani" o
"21 luglio" (linguaggio naturale, possibile se il modello non segue le
istruzioni, o se il campo viene manomesso dal browser prima di
/execute-action) veniva scritta così com'è sul CRM.

Verifica che una data non valida non provochi mai un'eccezione non gestita
né scriva un record, ma restituisca sempre un messaggio d'errore chiaro
("❌ ..." o {"error": ...} a seconda della funzione, stesso stile della
validazione dell'importo in test_ai_amount_validation.py).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest test_ai_expense_date_validation.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

from core.utils import now_iso
from services.ai_service import ai_service, _validate_expense_date


def run(coro):
    return asyncio.run(coro)


# ---------- _validate_expense_date ----------

def test_validate_expense_date_accetta_formato_corretto():
    assert _validate_expense_date("2026-07-21") == "2026-07-21"


def test_validate_expense_date_rifiuta_mese_e_giorno_inesistenti():
    assert _validate_expense_date("2026-15-80") is None


def test_validate_expense_date_rifiuta_linguaggio_naturale():
    assert _validate_expense_date("domani") is None
    assert _validate_expense_date("21 luglio") is None


def test_validate_expense_date_rifiuta_formato_sbagliato():
    # Formato valido in altri contesti (gg/mm/aaaa) ma non quello atteso
    # dall'input <input type="date"> della scheda di conferma.
    assert _validate_expense_date("21/07/2026") is None


# ---------- prepare_add_expense ----------

def test_prepare_expense_rifiuta_data_non_valida():
    result = run(ai_service.prepare_add_expense(
        {"category": "carburante", "amount": 40, "date": "2026-15-80"}, "u1"
    ))
    assert "error" in result


def test_prepare_expense_accetta_data_valida():
    result = run(ai_service.prepare_add_expense(
        {"category": "carburante", "amount": 40, "date": "2026-07-21"}, "u1"
    ))
    assert "error" not in result
    assert result["resolved_input"]["date"] == "2026-07-21"


def test_prepare_expense_usa_data_odierna_se_assente():
    result = run(ai_service.prepare_add_expense({"category": "carburante", "amount": 40}, "u1"))
    assert "error" not in result
    assert result["resolved_input"]["date"] == now_iso()[:10]


# ---------- _finalize_expense (chiamato anche direttamente da /execute-action) ----------

def test_finalize_expense_rifiuta_data_non_valida_senza_scrivere():
    msg = run(ai_service._finalize_expense(
        "u1", {"category": "vitto", "amount": 18, "date": "21 luglio"}
    ))
    assert msg.startswith("❌")


def test_finalize_expense_rifiuta_data_calendaristicamente_inesistente():
    msg = run(ai_service._finalize_expense(
        "u1", {"category": "vitto", "amount": 18, "date": "2026-15-80"}
    ))
    assert msg.startswith("❌")


# ---------- execute_crm_tool (percorso diretto per spese sotto soglia) ----------

def test_execute_crm_tool_add_expense_con_data_non_valida_non_esplode():
    result = run(ai_service.execute_crm_tool(
        "add_expense", {"category": "vitto", "amount": 18, "date": "domani"}, "u1"
    ))
    assert result.startswith("❌")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
