from pydantic import BaseModel
from typing import Optional

class LeadIn(BaseModel):
    company_name: str
    contact_name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    source: Optional[str] = ""
    estimated_value: Optional[float] = 0.0
    status: str = "nuovo"
    notes: Optional[str] = ""
    # Data (YYYY-MM-DD) del prossimo contatto pianificato, impostata
    # dall'agente — puramente informativa per ora, non letta da nessuna
    # automazione. updated_at/last_interaction_at/last_contact_at NON sono
    # qui: sono gestiti dal servizio, non modificabili liberamente da chi
    # chiama l'API (altrimenti si potrebbe falsificare "quando" è avvenuta
    # l'ultima interazione, il dato su cui si basa il trigger 'lead
    # inattivo' delle automazioni).
    next_follow_up_at: Optional[str] = None


class LeadContactIn(BaseModel):
    """Registra un contatto avvenuto davvero con il lead (chiamata, email,
    incontro) — a differenza di una modifica qualunque dei suoi dati,
    questo è il segnale esplicito che serve per non considerarlo più
    'inattivo' nelle automazioni."""
    note: Optional[str] = ""
