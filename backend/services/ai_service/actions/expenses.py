from core.utils import gen_id, now_iso
from models.expense import EXPENSE_CATEGORIES
from services.ai_service.catalog import _safe_float, _validate_expense_date


async def prepare_add_expense(client_repo, tool_input: dict, user_id: str) -> dict:
    """Normalizza i campi di una spesa SENZA scrivere sul DB. Usato per
    mostrare la scheda di conferma quando l'importo è elevato (o sempre,
    se il canale è voce).

    Se è indicato un cliente (es. "spesa di 40 euro con Rossi"), lo
    risolve qui server-side, come già avviene per client_name in
    prepare_add_offer: il browser non riceve mai la possibilità di
    scegliere client_id (non è tra gli ALLOWED_CONFIRM_EDITS), quindi una
    richiesta manomessa non può collegare la spesa a un cliente diverso
    da quello che l'utente ha realmente nominato in questo turno.

    A differenza delle offerte, un cliente non trovato non blocca la
    spesa: il collegamento è opzionale ("solo tracciamento", come da
    descrizione del tool), quindi la spesa viene comunque preparata,
    semplicemente senza client_id, con un avviso nel messaggio finale."""
    category = tool_input.get("category") or "altro"
    if category not in EXPENSE_CATEGORIES:
        category = "altro"
    amount = _safe_float(tool_input.get("amount"), 0)
    if amount <= 0:
        return {"error": "L'importo della spesa deve essere maggiore di zero."}
    raw_date = tool_input.get("date")
    if raw_date:
        date_ = _validate_expense_date(raw_date)
        if date_ is None:
            return {"error": "Data della spesa non valida: usa il formato AAAA-MM-DD."}
    else:
        date_ = now_iso()[:10]
    description = tool_input.get("description", "")
    notes = tool_input.get("notes", "")

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
        "tool_name": "add_expense",
        "summary": {
            "category": category,
            "amount": amount,
            "date": date_,
            "description": description,
            "client_name": client_name,
        },
        "resolved_input": {
            "category": category,
            "amount": amount,
            "date": date_,
            "description": description,
            "notes": notes,
            "client_id": client_id,
            "client_name": client_name,
            "client_not_found": client_not_found,
        },
    }


async def finalize_expense(expense_repo, user_id: str, resolved: dict) -> str:
    """Scrive davvero la spesa sul DB, a partire da un resolved_input già
    preparato da prepare_add_expense (eventualmente modificato
    dall'utente nella scheda di conferma). Il payload può arrivare anche
    direttamente da /api/ai/execute-action, quindi l'importo va validato
    di nuovo qui e non solo in prepare_add_expense."""
    category = resolved.get("category") or "altro"
    if category not in EXPENSE_CATEGORIES:
        category = "altro"
    amount = _safe_float(resolved.get("amount"), 0)
    if amount <= 0:
        return "❌ L'importo deve essere maggiore di zero: spesa non registrata."
    raw_date = resolved.get("date")
    if raw_date:
        date_ = _validate_expense_date(raw_date)
        if date_ is None:
            return "❌ Data della spesa non valida (usa il formato AAAA-MM-DD): spesa non registrata."
    else:
        date_ = now_iso()[:10]
    doc = {
        "id": gen_id(),
        "user_id": user_id,
        "date": date_,
        "category": category,
        "description": resolved.get("description", ""),
        "amount": amount,
        "client_id": resolved.get("client_id"),
        "notes": resolved.get("notes", ""),
        "receipt_document_id": None,
        "created_at": now_iso(),
    }
    await expense_repo.insert(doc)
    msg = f"✅ Spesa registrata: {category} - €{doc['amount']:.2f} ({doc['date']})."
    if resolved.get("client_name"):
        msg += f" Collegata al cliente {resolved['client_name']}."
    elif resolved.get("client_not_found"):
        msg += f" Cliente '{resolved['client_not_found']}' non trovato: spesa registrata senza collegamento."
    return msg
