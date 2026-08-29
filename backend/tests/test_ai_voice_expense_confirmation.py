"""
Verifica che le spese dettate via canale vocale richiedano SEMPRE conferma,
indipendentemente dall'importo.

Prima della fix, requires_confirmation() decideva se mostrare la scheda di
conferma per add_expense guardando solo l'importo (>= EXPENSE_CONFIRM_THRESHOLD),
ignorando il canale. Una spesa vocale sotto soglia (es. "Registra 18 euro di
benzina" dettato a voce) veniva quindi registrata subito, anche se il rischio
di trascrizione imprecisa di un importo è più alto proprio sul canale vocale.

Questo test chiama requires_confirmation() direttamente (è una funzione pura,
non serve mockare l'SDK Anthropic o il DB) per tutte le combinazioni
canale/importo/tool rilevanti.
"""

import sys

sys.path.insert(0, ".")

from services.ai_service import EXPENSE_CONFIRM_THRESHOLD, AiService

service = AiService.__new__(AiService)  # pure function, non serve __init__


def test_spesa_vocale_sotto_soglia_richiede_conferma():
    assert (
        service.requires_confirmation("add_expense", {"amount": 18}, channel="voice")
        is True
    )


def test_spesa_vocale_sopra_soglia_richiede_conferma():
    assert (
        service.requires_confirmation("add_expense", {"amount": 250}, channel="voice")
        is True
    )


def test_spesa_chat_sotto_soglia_resta_immediata():
    assert (
        service.requires_confirmation("add_expense", {"amount": 18}, channel="chat")
        is False
    )


def test_spesa_chat_sopra_soglia_richiede_conferma():
    assert (
        service.requires_confirmation("add_expense", {"amount": 250}, channel="chat")
        is True
    )


def test_spesa_esattamente_alla_soglia_richiede_conferma_anche_in_chat():
    assert (
        service.requires_confirmation(
            "add_expense", {"amount": EXPENSE_CONFIRM_THRESHOLD}, channel="chat"
        )
        is True
    )


def test_default_channel_e_chat_se_non_specificato():
    # Retro-compatibilità: chi chiama senza passare channel si comporta
    # come il canale chat (comportamento pre-esistente per spese basse).
    assert service.requires_confirmation("add_expense", {"amount": 18}) is False


def test_add_offer_richiede_sempre_conferma_indipendentemente_dal_canale():
    assert (
        service.requires_confirmation("add_offer", {"amount": 5}, channel="voice")
        is True
    )
    assert (
        service.requires_confirmation("add_offer", {"amount": 5}, channel="chat")
        is True
    )


def test_tool_non_economico_non_richiede_mai_conferma():
    assert service.requires_confirmation("add_client", {}, channel="voice") is False
    assert service.requires_confirmation("add_client", {}, channel="chat") is False


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
