"""
Test per la stima del costo delle chiamate AI in ai_service.py — in
particolare la correzione del 26/07/2026: il tool web_search ha un costo
separato dai token ($10 ogni 1000 ricerche) che prima non veniva conteggiato
nella stima esposta nel cruscotto di salute applicativa.

Prezzi verificati contro la tabella ufficiale
https://platform.claude.com/docs/en/about-claude/pricing il 26/07/2026:
Claude Haiku 4.5 = $1/MTok input, $5/MTok output (già corretti).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_ai_cost_estimate.py -v
"""

import sys
from types import SimpleNamespace

sys.path.insert(0, ".")

from services.ai_service import _estimate_cost_usd, _usage_tokens


def test_costo_solo_token_input_output():
    # 1000 token input (Haiku: $1/MTok) + 500 output (Haiku: $5/MTok)
    cost = _estimate_cost_usd(input_tokens=1_000_000, output_tokens=500_000)
    assert cost == 1.0 + 2.5  # $1.00 (input) + $2.50 (output)


def test_costo_include_ricerche_web():
    # 1000 ricerche web a $10 ogni 1000 = $10, oltre ai token
    cost = _estimate_cost_usd(input_tokens=0, output_tokens=0, web_searches=1000)
    assert cost == 10.0


def test_costo_combinato_token_e_ricerche():
    cost = _estimate_cost_usd(
        input_tokens=500_000, output_tokens=100_000, web_searches=3
    )
    # 0.5*$1 + 0.1*$5 + (3/1000)*$10 = 0.5 + 0.5 + 0.03
    assert round(cost, 6) == 1.03


def test_costo_zero_se_nessun_uso():
    assert _estimate_cost_usd(0, 0, 0) == 0.0


def test_usage_tokens_legge_i_valori_reali():
    message = SimpleNamespace(
        usage=SimpleNamespace(
            input_tokens=1200,
            output_tokens=340,
            server_tool_use=SimpleNamespace(web_search_requests=2),
        )
    )
    input_t, output_t, web_searches = _usage_tokens(message)
    assert (input_t, output_t, web_searches) == (1200, 340, 2)


def test_usage_tokens_senza_server_tool_use():
    # Risposta senza ricerche web: server_tool_use può essere assente
    message = SimpleNamespace(
        usage=SimpleNamespace(input_tokens=500, output_tokens=100)
    )
    input_t, output_t, web_searches = _usage_tokens(message)
    assert (input_t, output_t, web_searches) == (500, 100, 0)


def test_usage_tokens_senza_attributo_usage_non_crasha():
    # Doppio finto dell'SDK usato in altri test (es. test_ai_tool_forcing.py)
    # non ha .usage — non deve mai far fallire la conversazione.
    message = SimpleNamespace(content=[], stop_reason="end_turn")
    input_t, output_t, web_searches = _usage_tokens(message)
    assert (input_t, output_t, web_searches) == (0, 0, 0)
