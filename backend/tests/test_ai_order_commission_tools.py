"""
Verifica i tool AI add_order/add_commission (services/ai_service.py): come
add_offer e add_expense, generano un record economico e quindi richiedono
sempre la scheda di conferma prima di scrivere sul CRM — un ordine genera
automaticamente una provvigione, e una provvigione manuale lo è già di per
sé (vedi requires_confirmation).

Copre: prepare_*/_finalize_* per entrambi i tool, il gate di conferma, il
whitelist ALLOWED_CONFIRM_EDITS su execute_confirmed_action, il gate modulo
(ordini/provvigioni, moduli core opt-out) dentro chat(), e le mappe di
supporto (TOOL_MODULE, CRM_WRITE_TOOLS).

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    ANTHROPIC_API_KEY=test python -m pytest tests/test_ai_order_commission_tools.py -v
"""
import sys
import asyncio
from unittest.mock import patch, AsyncMock

sys.path.insert(0, ".")

import services.ai_service as ai_service_mod
from services.ai_service import CRM_WRITE_TOOLS, TOOL_MODULE
from tests.test_ai_tool_forcing import (
    build_service,
    build_service_with_offer,
    install_fake_anthropic,
    make_message,
    make_text_block,
    make_tool_use_block,
    Payload,
    FAKE_USER,
)


def run(coro):
    return asyncio.run(coro)


# ---------- Mappe di supporto ----------

def test_tool_module_e_crm_write_tools_registrano_i_nuovi_tool():
    assert TOOL_MODULE["add_order"] == "ordini"
    assert TOOL_MODULE["add_commission"] == "provvigioni"
    assert "add_order" in CRM_WRITE_TOOLS
    assert "add_commission" in CRM_WRITE_TOOLS


# ---------- requires_confirmation ----------

def test_add_order_richiede_sempre_conferma():
    service, _ = build_service()
    assert service.requires_confirmation("add_order", {}, "chat") is True
    assert service.requires_confirmation("add_order", {"total_amount": 1}, "voice") is True


def test_add_commission_richiede_sempre_conferma():
    service, _ = build_service()
    assert service.requires_confirmation("add_commission", {}, "chat") is True
    assert service.requires_confirmation("add_commission", {"amount": 1}, "voice") is True


# ---------- prepare_add_order ----------

def test_prepare_add_order_happy_path():
    service, offer_repo = build_service_with_offer()

    result = run(service.prepare_add_order(
        {"client_name": "Rossi", "mandante_name": "Paginesi", "total_amount": 1200, "sale_type": "rinnovo"},
        FAKE_USER["id"],
    ))

    assert "error" not in result
    assert result["tool_name"] == "add_order"
    assert result["resolved_input"]["client_id"] == "c-1"
    assert result["resolved_input"]["mandante_id"] == "m-1"
    assert result["resolved_input"]["amount"] == 1200
    assert result["resolved_input"]["sale_type"] == "rinnovo"
    assert result["resolved_input"]["status"] == "confermato"
    assert result["resolved_input"]["payment_status"] == "non_pagato"
    assert offer_repo.docs == []  # nessuna scrittura in fase di prepare


def test_prepare_add_order_cliente_non_trovato():
    service, _ = build_service_with_offer()

    result = run(service.prepare_add_order(
        {"client_name": "Cliente Inesistente", "mandante_name": "Paginesi", "total_amount": 500}, FAKE_USER["id"],
    ))

    assert "error" in result
    assert "Cliente Inesistente" in result["error"]


def test_prepare_add_order_mandante_non_trovato():
    service, _ = build_service_with_offer()

    result = run(service.prepare_add_order(
        {"client_name": "Rossi", "mandante_name": "Mandante Inesistente", "total_amount": 500}, FAKE_USER["id"],
    ))

    assert "error" in result
    assert "Mandante Inesistente" in result["error"]


def test_prepare_add_order_importo_zero_e_errore():
    service, _ = build_service_with_offer()

    result = run(service.prepare_add_order(
        {"client_name": "Rossi", "mandante_name": "Paginesi", "total_amount": 0}, FAKE_USER["id"],
    ))

    assert "error" in result


def test_prepare_add_order_stato_non_valido_ricade_su_confermato():
    service, _ = build_service_with_offer()

    result = run(service.prepare_add_order(
        {"client_name": "Rossi", "mandante_name": "Paginesi", "total_amount": 500, "status": "stato-fantasioso"},
        FAKE_USER["id"],
    ))

    assert result["resolved_input"]["status"] == "confermato"


# ---------- _finalize_add_order ----------

def test_finalize_add_order_happy_path_delega_a_order_service():
    service, _ = build_service_with_offer()

    with patch("services.ai_service.order_service") as mock_order_service:
        mock_order_service.create_order = AsyncMock(return_value={"id": "o-1", "numero_ordine": "ORD-0001", "total": 1000})
        msg = run(service._finalize_add_order(FAKE_USER["id"], {
            "client_id": "c-1", "client_name": "Rossi Srl",
            "mandante_id": "m-1", "mandante_name": "Paginesi",
            "items": [{"product_id": None, "description": "Ordine Rossi Srl", "quantity": 1, "unit_price": 1000, "discount": 0}],
            "amount": 1000, "sale_type": "nuovo", "status": "confermato",
            "payment_status": "non_pagato", "notes": "",
        }))

    assert mock_order_service.create_order.await_count == 1
    called_user, order_in = mock_order_service.create_order.await_args.args
    assert called_user == {"id": FAKE_USER["id"]}
    assert order_in.client_id == "c-1"
    assert order_in.mandante_id == "m-1"
    assert msg.startswith("✅")
    assert "ORD-0001" in msg
    assert "Provvigione generata" in msg
    assert "€100.00" in msg  # aliquota 10% di 1000


def test_finalize_add_order_annullato_non_genera_provvigione():
    service, _ = build_service_with_offer()

    with patch("services.ai_service.order_service") as mock_order_service:
        mock_order_service.create_order = AsyncMock(return_value={"id": "o-1", "numero_ordine": "ORD-0002", "total": 500})
        msg = run(service._finalize_add_order(FAKE_USER["id"], {
            "client_id": "c-1", "client_name": "Rossi Srl",
            "mandante_id": "m-1", "mandante_name": "Paginesi",
            "items": [{"product_id": None, "description": "Ordine", "quantity": 1, "unit_price": 500, "discount": 0}],
            "amount": 500, "sale_type": "nuovo", "status": "annullato",
            "payment_status": "non_pagato", "notes": "",
        }))

    assert msg.startswith("✅")
    assert "Provvigione" not in msg


def test_finalize_add_order_importo_modificato_ricalcola_items():
    service, _ = build_service_with_offer()

    with patch("services.ai_service.order_service") as mock_order_service:
        mock_order_service.create_order = AsyncMock(return_value={"id": "o-1", "numero_ordine": "ORD-0003", "total": 2000})
        run(service._finalize_add_order(FAKE_USER["id"], {
            "client_id": "c-1", "client_name": "Rossi Srl",
            "mandante_id": "m-1", "mandante_name": "Paginesi",
            "items": [{"product_id": "p-1", "description": "Prodotto", "quantity": 1, "unit_price": 1000, "discount": 0}],
            "amount": 2000, "sale_type": "nuovo", "status": "confermato",
            "payment_status": "non_pagato", "notes": "",
        }))

    called_user, order_in = mock_order_service.create_order.await_args.args
    assert len(order_in.items) == 1
    assert order_in.items[0].unit_price == 2000


def test_finalize_add_order_mandante_non_piu_trovato():
    service, _ = build_service_with_offer()

    msg = run(service._finalize_add_order(FAKE_USER["id"], {
        "client_id": "c-1", "client_name": "Rossi Srl",
        "mandante_id": "m-non-esiste-piu", "mandante_name": "Paginesi",
        "items": [{"product_id": None, "description": "Ordine", "quantity": 1, "unit_price": 500, "discount": 0}],
        "amount": 500, "sale_type": "nuovo", "status": "confermato",
        "payment_status": "non_pagato", "notes": "",
    }))

    assert msg.startswith("❌")


# ---------- prepare_add_commission ----------

def test_prepare_add_commission_happy_path_con_mandante_e_cliente():
    service, _ = build_service_with_offer()

    result = run(service.prepare_add_commission(
        {"amount": 300, "period": "2026-05", "mandante_name": "Paginesi", "client_name": "Rossi",
         "tipo": "bonus", "stato": "incassato", "descrizione": "Premio trimestrale"},
        FAKE_USER["id"],
    ))

    assert "error" not in result
    ri = result["resolved_input"]
    assert ri["mandante_id"] == "m-1"
    assert ri["mandante_not_found"] is None
    assert ri["client_id"] == "c-1"
    assert ri["client_not_found"] is None
    assert ri["period"] == "2026-05"
    assert ri["tipo"] == "bonus"
    assert ri["stato"] == "incassato"
    assert ri["descrizione"] == "Premio trimestrale"


def test_prepare_add_commission_senza_mandante_ne_cliente():
    service, _ = build_service()

    result = run(service.prepare_add_commission({"amount": 150}, FAKE_USER["id"]))

    assert "error" not in result
    ri = result["resolved_input"]
    assert ri["mandante_id"] is None
    assert ri["mandante_not_found"] is None
    assert ri["client_id"] is None
    assert ri["client_not_found"] is None


def test_prepare_add_commission_mandante_e_cliente_non_trovati_non_blocca():
    service, _ = build_service()

    result = run(service.prepare_add_commission(
        {"amount": 150, "mandante_name": "Mandante Fantasma", "client_name": "Cliente Fantasma"},
        FAKE_USER["id"],
    ))

    assert "error" not in result
    ri = result["resolved_input"]
    assert ri["mandante_id"] is None
    assert ri["mandante_not_found"] == "Mandante Fantasma"
    assert ri["client_id"] is None
    assert ri["client_not_found"] == "Cliente Fantasma"


def test_prepare_add_commission_importo_zero_e_errore():
    service, _ = build_service()

    result = run(service.prepare_add_commission({"amount": 0}, FAKE_USER["id"]))

    assert "error" in result


def test_prepare_add_commission_periodo_mancante_usa_mese_corrente():
    service, _ = build_service()

    result = run(service.prepare_add_commission({"amount": 100}, FAKE_USER["id"]))

    assert result["resolved_input"]["period"] is not None
    import re
    assert re.match(r"^\d{4}-\d{2}$", result["resolved_input"]["period"])


def test_prepare_add_commission_periodo_non_valido_e_errore():
    service, _ = build_service()

    result = run(service.prepare_add_commission({"amount": 100, "period": "non-un-mese"}, FAKE_USER["id"]))

    assert "error" in result


def test_prepare_add_commission_stato_e_tipo_fuori_enum_ricadono_sui_default():
    service, _ = build_service()

    result = run(service.prepare_add_commission(
        {"amount": 100, "stato": "boh", "tipo": "boh"}, FAKE_USER["id"],
    ))

    assert result["resolved_input"]["stato"] == "maturato"
    assert result["resolved_input"]["tipo"] == "ordinaria"


# ---------- _finalize_add_commission ----------

def test_finalize_add_commission_happy_path_delega_a_commission_service():
    service, _ = build_service()

    with patch("services.ai_service.commission_service") as mock_commission_service:
        mock_commission_service.create_manual_commission = AsyncMock(return_value={"id": "mc-1"})
        msg = run(service._finalize_add_commission(FAKE_USER["id"], {
            "period": "2026-05", "amount": 300, "stato": "maturato", "tipo": "ordinaria",
            "descrizione": "Premio", "note": "", "mandante_id": "m-1", "mandante_name": "Paginesi",
            "client_id": None, "client_name": None, "client_not_found": None,
        }))

    assert mock_commission_service.create_manual_commission.await_count == 1
    called_user, fields = mock_commission_service.create_manual_commission.await_args.args
    assert called_user == {"id": FAKE_USER["id"]}
    assert isinstance(fields, dict)  # dict semplice, non un'istanza ManualCommissionIn
    assert fields["period"] == "2026-05"
    assert fields["amount"] == 300
    assert fields["mandante_id"] == "m-1"
    assert msg.startswith("✅")
    assert "Paginesi" in msg


def test_finalize_add_commission_avvisa_se_mandante_non_trovato():
    service, _ = build_service()

    with patch("services.ai_service.commission_service") as mock_commission_service:
        mock_commission_service.create_manual_commission = AsyncMock(return_value={"id": "mc-1"})
        msg = run(service._finalize_add_commission(FAKE_USER["id"], {
            "period": "2026-05", "amount": 100, "stato": "maturato", "tipo": "ordinaria",
            "descrizione": "", "note": "", "mandante_id": None, "mandante_name": None,
            "mandante_not_found": "Mandante Fantasma", "client_id": None, "client_name": None,
        }))

    assert msg.startswith("✅")
    assert "non trovato" in msg


def test_finalize_add_commission_importo_zero_non_scrive():
    service, _ = build_service()

    with patch("services.ai_service.commission_service") as mock_commission_service:
        mock_commission_service.create_manual_commission = AsyncMock(return_value={"id": "mc-1"})
        msg = run(service._finalize_add_commission(FAKE_USER["id"], {"amount": 0}))

    assert msg.startswith("❌")
    mock_commission_service.create_manual_commission.assert_not_called()


# ---------- Integrazione loop chat: pending_actions ----------

def test_add_order_non_scrive_subito_ma_richiede_conferma():
    responses = {
        "responses": [
            make_message(
                [make_tool_use_block(
                    "add_order",
                    {"client_name": "Rossi", "mandante_name": "Paginesi", "total_amount": 900},
                    "tu_1",
                )],
                stop_reason="tool_use",
            ),
            make_message(
                [make_text_block("Ho preparato l'ordine per Rossi Srl da 900€, conferma per registrarlo.")],
                stop_reason="end_turn",
            ),
        ]
    }
    install_fake_anthropic(responses)
    service, offer_repo = build_service_with_offer()

    result = run(service.chat(FAKE_USER, Payload("registra un ordine di 900 euro per Rossi con Paginesi")))

    assert result["actions"] == []
    assert offer_repo.docs == []
    assert len(result["pending_actions"]) == 1
    pending = result["pending_actions"][0]
    assert pending["tool_name"] == "add_order"
    assert pending["summary"]["amount"] == 900


def test_add_commission_non_scrive_subito_ma_richiede_conferma():
    responses = {
        "responses": [
            make_message(
                [make_tool_use_block("add_commission", {"amount": 250, "tipo": "bonus"}, "tu_1")],
                stop_reason="tool_use",
            ),
            make_message(
                [make_text_block("Ho preparato la provvigione manuale da 250€, conferma per registrarla.")],
                stop_reason="end_turn",
            ),
        ]
    }
    install_fake_anthropic(responses)
    service, _ = build_service()

    result = run(service.chat(FAKE_USER, Payload("registra una provvigione manuale di 250 euro come bonus")))

    assert result["actions"] == []
    assert len(result["pending_actions"]) == 1
    pending = result["pending_actions"][0]
    assert pending["tool_name"] == "add_commission"
    assert pending["summary"]["amount"] == 250


# ---------- ALLOWED_CONFIRM_EDITS enforcement ----------

def _prepare_pending_order(service):
    return run(service._log_action(
        FAKE_USER["id"], "chat", "registra ordine 900 euro Rossi Paginesi", "add_order",
        {"client_name": "Rossi", "mandante_name": "Paginesi", "total_amount": 900},
        status="in_attesa",
        resolved_params={
            "client_id": "c-1", "client_name": "Rossi Srl",
            "mandante_id": "m-1", "mandante_name": "Paginesi",
            "items": [{"product_id": None, "description": "Ordine Rossi Srl", "quantity": 1, "unit_price": 900, "discount": 0}],
            "amount": 900, "sale_type": "nuovo", "status": "confermato",
            "payment_status": "non_pagato", "notes": "",
        },
    ))


def test_execute_confirmed_action_add_order_ignora_client_id_manomesso():
    service, _ = build_service_with_offer()
    log = _prepare_pending_order(service)

    tampered = dict(log["resolved_params"])
    tampered["client_id"] = "c-di-un-altro-utente"
    tampered["mandante_id"] = "m-di-un-altro-utente"

    with patch("services.ai_service.order_service") as mock_order_service:
        mock_order_service.create_order = AsyncMock(return_value={"id": "o-1", "numero_ordine": "ORD-1", "total": 900})
        run(service.execute_confirmed_action(FAKE_USER, {
            "tool_name": "add_order", "resolved_input": tampered, "log_id": log["id"],
        }))

    called_user, order_in = mock_order_service.create_order.await_args.args
    assert order_in.client_id == "c-1"
    assert order_in.mandante_id == "m-1"


def test_execute_confirmed_action_add_order_amount_e_status_restano_modificabili():
    service, _ = build_service_with_offer()
    log = _prepare_pending_order(service)

    edited = dict(log["resolved_params"])
    edited["amount"] = 1800
    edited["status"] = "annullato"

    with patch("services.ai_service.order_service") as mock_order_service:
        mock_order_service.create_order = AsyncMock(return_value={"id": "o-1", "numero_ordine": "ORD-1", "total": 1800})
        result = run(service.execute_confirmed_action(FAKE_USER, {
            "tool_name": "add_order", "resolved_input": edited, "log_id": log["id"],
        }))

    called_user, order_in = mock_order_service.create_order.await_args.args
    assert order_in.status == "annullato"
    assert "✅" in result["message"]
    assert "Provvigione" not in result["message"]


def test_execute_confirmed_action_add_order_senza_client_id_fallisce():
    service, _ = build_service_with_offer()
    log = run(service._log_action(
        FAKE_USER["id"], "chat", "registra ordine", "add_order", {},
        status="in_attesa",
        resolved_params={"client_id": None, "mandante_id": "m-1", "amount": 500},
    ))

    try:
        run(service.execute_confirmed_action(FAKE_USER, {
            "tool_name": "add_order", "resolved_input": {}, "log_id": log["id"],
        }))
        assert False, "doveva sollevare HTTPException"
    except Exception as e:
        assert getattr(e, "status_code", None) == 400


def _prepare_pending_commission(service):
    return run(service._log_action(
        FAKE_USER["id"], "chat", "registra provvigione manuale 300 euro", "add_commission",
        {"amount": 300},
        status="in_attesa",
        resolved_params={
            "period": "2026-05", "amount": 300, "stato": "maturato", "tipo": "ordinaria",
            "descrizione": "", "note": "", "mandante_id": "m-1", "mandante_name": "Paginesi",
            "mandante_not_found": None, "client_id": None, "client_name": None, "client_not_found": None,
        },
    ))


def test_execute_confirmed_action_add_commission_ignora_mandante_id_manomesso():
    service, _ = build_service_with_offer()
    log = _prepare_pending_commission(service)

    tampered = dict(log["resolved_params"])
    tampered["mandante_id"] = "m-di-un-altro-utente"
    tampered["client_id"] = "c-di-un-altro-utente"

    with patch("services.ai_service.commission_service") as mock_commission_service:
        mock_commission_service.create_manual_commission = AsyncMock(return_value={"id": "mc-1"})
        run(service.execute_confirmed_action(FAKE_USER, {
            "tool_name": "add_commission", "resolved_input": tampered, "log_id": log["id"],
        }))

    called_user, fields = mock_commission_service.create_manual_commission.await_args.args
    assert fields["mandante_id"] == "m-1"
    assert fields["client_id"] is None


def test_execute_confirmed_action_add_commission_amount_stato_tipo_descrizione_period_restano_modificabili():
    service, _ = build_service_with_offer()
    log = _prepare_pending_commission(service)

    edited = dict(log["resolved_params"])
    edited["amount"] = 500
    edited["stato"] = "incassato"
    edited["tipo"] = "rettifica"
    edited["descrizione"] = "Corretto a mano"
    edited["period"] = "2026-06"

    with patch("services.ai_service.commission_service") as mock_commission_service:
        mock_commission_service.create_manual_commission = AsyncMock(return_value={"id": "mc-1"})
        result = run(service.execute_confirmed_action(FAKE_USER, {
            "tool_name": "add_commission", "resolved_input": edited, "log_id": log["id"],
        }))

    called_user, fields = mock_commission_service.create_manual_commission.await_args.args
    assert fields["amount"] == 500
    assert fields["stato"] == "incassato"
    assert fields["tipo"] == "rettifica"
    assert fields["descrizione"] == "Corretto a mano"
    assert fields["period"] == "2026-06"
    assert "✅" in result["message"]


# ---------- Gate modulo (ordini/provvigioni, moduli core opt-out) ----------

def test_add_order_bloccato_se_modulo_ordini_disattivato():
    responses = {"responses": [
        make_message([make_tool_use_block(
            "add_order", {"client_name": "Rossi", "mandante_name": "Paginesi", "total_amount": 500}, "t1",
        )], stop_reason="tool_use"),
        make_message([make_text_block("Fatto.")], stop_reason="end_turn"),
    ]}
    install_fake_anthropic(responses)
    service, offer_repo = build_service_with_offer()
    user = dict(FAKE_USER, disabled_modules=["ordini"])

    result = run(service.chat(user, Payload("registra un ordine di 500 euro per Rossi con Paginesi")))

    assert result["pending_actions"] == []
    assert offer_repo.docs == []
    log = next(d for d in service.action_log_repo.docs if d["tool_name"] == "add_order")
    assert log["status"] == "fallita"
    assert "🔒" in log["result"]


def test_add_commission_bloccato_se_modulo_provvigioni_disattivato():
    responses = {"responses": [
        make_message([make_tool_use_block("add_commission", {"amount": 300}, "t1")], stop_reason="tool_use"),
        make_message([make_text_block("Fatto.")], stop_reason="end_turn"),
    ]}
    install_fake_anthropic(responses)
    service, _ = build_service()
    user = dict(FAKE_USER, disabled_modules=["provvigioni"])

    result = run(service.chat(user, Payload("registra una provvigione manuale di 300 euro")))

    assert result["pending_actions"] == []
    log = next(d for d in service.action_log_repo.docs if d["tool_name"] == "add_commission")
    assert log["status"] == "fallita"
    assert "🔒" in log["result"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
