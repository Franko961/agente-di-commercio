"""Migrazione una tantum: il tool AI add_lead
(services/ai_service/tools/crm_writer.py) scriveva "status": "aperto" invece
di un valore valido di LEAD_STATUSES ("nuovo", "contattato", "qualificato",
"trattativa", "vinto", "perso") — un bug scoperto perché rendeva il lead
invisibile in ogni colonna della pipeline Kanban (frontend/src/pages/
Leads.jsx filtra strettamente `l.status === col.id`, nessuna vista
alternativa che ignori lo stato: né la board né la ricerca lo mostravano).
Segnalato da Franco il 2026-09-12 ("ho chiesto all'AI di aggiungere un lead,
non riesco a visualizzarlo").

Il tool è stato corretto per i lead futuri; questa migrazione ripara
retroattivamente ogni lead già creato con uno status non valido (compreso
il caso limite di un lead senza il campo status affatto — $nin lo intercetta
comunque, un campo assente non è "nella lista" LEAD_STATUSES), riportandolo
a "nuovo": lo stesso stato iniziale che avrebbe dovuto avere fin dall'inizio.
"""

from core.database import db
from models.lead import LEAD_STATUSES


async def run() -> None:
    await db.leads.update_many(
        {"status": {"$nin": LEAD_STATUSES}},
        {"$set": {"status": "nuovo"}},
    )
