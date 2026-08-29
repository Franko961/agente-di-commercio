import logging

from fastapi import HTTPException

from core.utils import now_iso
from services.ai_service.catalog import EXPENSE_CONFIRM_THRESHOLD, _safe_float

logger = logging.getLogger(__name__)

# Campi che la scheda di conferma (AIActionConfirm.jsx) permette davvero
# di modificare per ciascun tool economico — riflette esattamente cosa
# espone l'interfaccia (importo/stato per le offerte; importo/categoria/
# data/descrizione per le spese). Ogni altro campo del resolved_input
# inviato dal browser (client_id, mandante_id, items/prodotti, title,
# ecc.) viene ignorato: execute_confirmed_action lo recupera sempre dal
# registro azioni (calcolato server-side al momento della proposta),
# così una richiesta manomessa non può far scrivere un cliente, un
# mandante o dei prodotti diversi da quelli che l'utente ha realmente
# visto sulla scheda.
ALLOWED_CONFIRM_EDITS = {
    "add_offer": {"amount", "accepted", "sale_type"},
    "add_order": {"amount", "sale_type", "status"},
    "add_expense": {"amount", "category", "date", "description"},
    "add_commission": {"amount", "stato", "tipo", "descrizione", "period"},
}


def requires_confirmation(
    tool_name: str, tool_input: dict, channel: str = "chat"
) -> bool:
    """True se il tool genera un record economico e va sempre mostrato
    come scheda di conferma prima di essere eseguito davvero: le vendite/
    offerte, gli ordini e le provvigioni manuali sempre (un ordine genera
    automaticamente una provvigione, e una provvigione manuale lo è già
    di per sé); le spese solo sopra EXPENSE_CONFIRM_THRESHOLD (le piccole
    spese di routine, es. un rifornimento, restano immediate) — tranne
    quando il comando arriva dal canale vocale, dove una trascrizione
    imprecisa dell'importo può creare una spesa senza che l'utente
    l'abbia davvero rivista: in quel caso la conferma è sempre richiesta,
    indipendentemente dall'importo."""
    if tool_name in ("add_offer", "add_order", "add_commission"):
        return True
    if tool_name == "add_expense":
        amount = _safe_float(tool_input.get("amount"), 0)
        return channel == "voice" or amount >= EXPENSE_CONFIRM_THRESHOLD
    return False


async def execute_confirmed_action(service, user: dict, payload: dict) -> dict:
    """Esegue un'azione economica (vendita/offerta o spesa) dopo che
    l'utente l'ha confermata (eventualmente modificata) sulla scheda di
    conferma mostrata in chat. Non richiama mai il modello: i dati sono
    già quelli che l'utente ha rivisto e approvato.

    Prima di eseguire, verifica che il log_id esista, appartenga
    all'utente, sia ancora "in_attesa" e corrisponda al tool richiesto;
    poi lo sposta atomicamente a "in_esecuzione" (compare-and-swap sullo
    stato). Solo la richiesta che vince questa transizione procede
    davvero: un doppio clic, un retry di rete o una richiesta duplicata
    con lo stesso log_id ricevono un 409 invece di generare due volte la
    stessa offerta/ordine/provvigione/spesa.

    Il resolved_input inviato dal browser non viene mai usato così com'è:
    il backend parte dal resolved_params salvato nel log (calcolato
    server-side da prepare_add_offer/prepare_add_expense al momento della
    proposta) e vi sovrascrive solo i campi che ALLOWED_CONFIRM_EDITS
    permette di modificare per quel tool. Cliente, mandante e prodotti
    arrivano quindi sempre dal registro, mai dal payload del browser: una
    richiesta manomessa (es. un client_id di un altro utente, o un
    mandante diverso) non può alterare cosa viene effettivamente scritto
    sul CRM."""
    action_log_repo = service.action_log_repo
    tool_name = payload.get("tool_name")
    browser_input = payload.get("resolved_input") or {}
    log_id = payload.get("log_id")

    if tool_name not in ("add_offer", "add_expense", "add_order", "add_commission"):
        raise HTTPException(400, "Tipo di azione non valido o non richiede conferma.")
    if not log_id:
        raise HTTPException(400, "Azione non tracciata: log_id mancante.")

    log = await action_log_repo.find_one(log_id, user["id"])
    if not log:
        raise HTTPException(404, "Azione non trovata.")
    if log.get("tool_name") != tool_name:
        raise HTTPException(400, "Il tipo di azione non corrisponde al registro.")
    if log.get("status") != "in_attesa":
        raise HTTPException(409, "Azione già elaborata.")

    claimed = await action_log_repo.transition(
        log_id,
        user["id"],
        "in_attesa",
        {"status": "in_esecuzione", "execution_started_at": now_iso()},
        extra_match={"tool_name": tool_name},
    )
    if not claimed:
        # Un'altra richiesta concorrente ha vinto la transizione tra il
        # find_one sopra e questo punto (finestra di race condition):
        # questa richiesta non esegue nulla.
        raise HTTPException(409, "Azione già elaborata.")

    # Base fidata: i dati che il server aveva già risolto e mostrato
    # nella scheda di conferma. Il payload del browser può modificare
    # solo i campi esplicitamente concessi per questo tool.
    resolved = dict(log.get("resolved_params") or {})
    allowed = ALLOWED_CONFIRM_EDITS.get(tool_name, set())
    for key in allowed:
        if key in browser_input:
            resolved[key] = browser_input[key]

    if tool_name in ("add_offer", "add_order") and (
        not resolved.get("client_id") or not resolved.get("mandante_id")
    ):
        await action_log_repo.update_by_id(
            log_id,
            user["id"],
            {
                "status": "fallita",
                "result": "Dati mancanti per registrare la vendita.",
                "confirmed_at": now_iso(),
            },
        )
        raise HTTPException(400, "Dati mancanti per registrare la vendita.")

    if tool_name == "add_offer":
        message = await service._finalize_offer(user["id"], resolved)
    elif tool_name == "add_order":
        message = await service._finalize_add_order(user["id"], resolved)
    elif tool_name == "add_commission":
        message = await service._finalize_add_commission(user["id"], resolved)
    else:
        message = await service._finalize_expense(user["id"], resolved)

    try:
        await action_log_repo.update_by_id(
            log_id,
            user["id"],
            {
                "status": "fallita" if message.startswith("❌") else "confermata",
                "final_params": resolved,
                "result": message,
                "confirmed_at": now_iso(),
            },
        )
    except Exception as e:
        logger.error(f"AI action log confirm error: {e}")

    return {"message": message}
