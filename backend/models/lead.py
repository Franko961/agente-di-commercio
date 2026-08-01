from pydantic import BaseModel, Field
from typing import Literal, Optional
from core.validation_limits import SHORT_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH, MAX_MONETARY_TARGET

LEAD_STATUSES = ["nuovo", "contattato", "qualificato", "trattativa", "vinto", "perso"]


class LeadIn(BaseModel):
    company_name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    contact_name: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    email: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    phone: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    source: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    # Prima senza alcun limite, nemmeno inferiore: un valore negativo o
    # assurdo restava salvato così com'è (mostrato in lista/export CSV).
    estimated_value: Optional[float] = Field(0.0, ge=0, le=MAX_MONETARY_TARGET)
    status: Literal[*LEAD_STATUSES] = "nuovo"
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    # Data (YYYY-MM-DD) del prossimo contatto pianificato, impostata
    # dall'agente — puramente informativa per ora, non letta da nessuna
    # automazione. updated_at/last_interaction_at/last_contact_at NON sono
    # qui: sono gestiti dal servizio, non modificabili liberamente da chi
    # chiama l'API (altrimenti si potrebbe falsificare "quando" è avvenuta
    # l'ultima interazione, il dato su cui si basa il trigger 'lead
    # inattivo' delle automazioni).
    next_follow_up_at: Optional[str] = None


class LeadStatusIn(BaseModel):
    status: Literal[*LEAD_STATUSES]


class LeadContactIn(BaseModel):
    """Registra un contatto avvenuto davvero con il lead (chiamata, email,
    incontro) — a differenza di una modifica qualunque dei suoi dati,
    questo è il segnale esplicito che serve per non considerarlo più
    'inattivo' nelle automazioni."""
    note: Optional[str] = ""
