"""Rileva il primo momento in cui un utente (tipicamente un account in prova
appena creato da una richiesta demo) compie un'azione reale nel CRM — crea un
cliente, un lead o un ordine, qualunque sia il primo che capita — per dare
visibilità sull'imbuto di attivazione oltre a form_start/login/onboarding
(vedi analytics.js lato frontend). Non è un dato di prodotto: serve solo a
GA4 per l'evento "first_real_action", letto dal frontend nel campo aggiunto
alla risposta di creazione (client_service, lead_service, order_service)."""

from core.database import db
from core.utils import now_iso


async def mark_first_action_if_needed(user_id: str) -> bool:
    """find_one_and_update con il filtro "not yet set" è atomico e quindi
    race-safe: ritorna un documento (quindi True) SOLO per la chiamata che
    riesce davvero a impostare activated_at, mai per due richieste
    concorrenti sullo stesso utente né per le successive una volta già
    impostato — così il frontend traccia l'evento esattamente una volta per
    account, indipendentemente da quale dei tre domini (cliente/lead/ordine)
    sia stato il primo."""
    doc = await db.users.find_one_and_update(
        {"id": user_id, "activated_at": {"$exists": False}},
        {"$set": {"activated_at": now_iso()}},
    )
    return doc is not None
