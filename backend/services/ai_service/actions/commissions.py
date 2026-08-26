from core.utils import now_local
from core.validation_limits import MAX_MONETARY_TARGET, SHORT_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH
from services.ai_service.catalog import _safe_float, _validate_commission_period
from services.commission_service import commission_service


async def prepare_add_commission(mandante_repo, client_repo, tool_input: dict, user_id: str) -> dict:
    """Normalizza i campi di una provvigione manuale SENZA scrivere sul
    DB. Usato per mostrare la scheda di conferma: una provvigione manuale
    è sempre un record economico (non solo un tracciamento come una
    spesa), quindi richiede sempre conferma, indipendentemente
    dall'importo — vedi requires_confirmation.

    Mandante e cliente sono entrambi opzionali (stesso principio di
    prepare_add_expense per il cliente): se indicati ma non trovati, la
    provvigione viene comunque preparata senza il collegamento, con un
    avviso nel messaggio finale."""
    amount = _safe_float(tool_input.get("amount"), 0)
    if amount <= 0:
        return {"error": "L'importo della provvigione deve essere maggiore di zero."}
    if amount > MAX_MONETARY_TARGET:
        return {"error": "L'importo della provvigione supera il massimo consentito."}

    raw_period = tool_input.get("period")
    if raw_period:
        period = _validate_commission_period(raw_period)
        if period is None:
            return {"error": "Periodo non valido: usa il formato AAAA-MM."}
    else:
        period = now_local().strftime("%Y-%m")

    stato = tool_input.get("stato") or "maturato"
    if stato not in ("maturato", "incassato"):
        stato = "maturato"
    tipo = tool_input.get("tipo") or "ordinaria"
    if tipo not in ("ordinaria", "bonus", "rettifica"):
        tipo = "ordinaria"
    descrizione = (tool_input.get("descrizione") or "")[:SHORT_TEXT_MAX_LENGTH]
    note = (tool_input.get("note") or "")[:LONG_TEXT_MAX_LENGTH]

    mandante_id = None
    mandante_name = None
    mandante_not_found = None
    requested_mandante_name = tool_input.get("mandante_name")
    if requested_mandante_name:
        mand = await mandante_repo.find_by_name_regex(user_id, requested_mandante_name)
        if mand:
            mandante_id = mand["id"]
            mandante_name = mand["name"]
        else:
            mandante_not_found = requested_mandante_name

    client_id = None
    client_name = None
    client_not_found = None
    requested_client_name = tool_input.get("client_name")
    if requested_client_name:
        cli = await client_repo.find_by_name_regex(user_id, requested_client_name)
        if cli:
            client_id = cli["id"]
            client_name = cli["company_name"]
        else:
            client_not_found = requested_client_name

    return {
        "tool_name": "add_commission",
        "summary": {
            "period": period, "amount": amount, "stato": stato, "tipo": tipo,
            "descrizione": descrizione, "mandante_name": mandante_name, "client_name": client_name,
        },
        "resolved_input": {
            "period": period, "amount": amount, "stato": stato, "tipo": tipo,
            "descrizione": descrizione, "note": note,
            "mandante_id": mandante_id, "mandante_name": mandante_name, "mandante_not_found": mandante_not_found,
            "client_id": client_id, "client_name": client_name, "client_not_found": client_not_found,
        },
    }


async def finalize_add_commission(user_id: str, resolved: dict) -> str:
    """Scrive davvero la provvigione manuale sul DB, a partire da un
    resolved_input già preparato da prepare_add_commission (eventualmente
    modificato dall'utente sulla scheda di conferma). Il payload può
    arrivare anche direttamente da /api/ai/execute-action, quindi va
    ri-validato qui, non solo in prepare_add_commission."""
    amount = _safe_float(resolved.get("amount"), 0)
    if amount <= 0:
        return "❌ L'importo deve essere maggiore di zero: provvigione non registrata."
    if amount > MAX_MONETARY_TARGET:
        return "❌ L'importo supera il massimo consentito: provvigione non registrata."

    raw_period = resolved.get("period")
    period = _validate_commission_period(raw_period) if raw_period else None
    if period is None:
        period = now_local().strftime("%Y-%m")

    stato = resolved.get("stato") or "maturato"
    if stato not in ("maturato", "incassato"):
        stato = "maturato"
    tipo = resolved.get("tipo") or "ordinaria"
    if tipo not in ("ordinaria", "bonus", "rettifica"):
        tipo = "ordinaria"
    descrizione = (resolved.get("descrizione") or "")[:SHORT_TEXT_MAX_LENGTH]
    note = (resolved.get("note") or "")[:LONG_TEXT_MAX_LENGTH]

    fields = {
        "period": period, "amount": amount, "mandante_id": resolved.get("mandante_id"),
        "client_id": resolved.get("client_id"), "descrizione": descrizione,
        "stato": stato, "note": note, "tipo": tipo,
    }
    await commission_service.create_manual_commission({"id": user_id}, fields)

    msg = f"✅ Provvigione manuale registrata per {period}: €{amount:.2f} ({tipo}, {stato})."
    if resolved.get("mandante_name"):
        msg += f" Collegata al mandante {resolved['mandante_name']}."
    elif resolved.get("mandante_not_found"):
        msg += f" Mandante '{resolved['mandante_not_found']}' non trovato: provvigione registrata senza collegamento."
    if resolved.get("client_name"):
        msg += f" Cliente collegato: {resolved['client_name']}."
    elif resolved.get("client_not_found"):
        msg += f" Cliente '{resolved['client_not_found']}' non trovato: provvigione registrata senza collegamento."
    return msg
