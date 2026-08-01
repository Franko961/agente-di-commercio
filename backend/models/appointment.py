from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from core.validation_limits import SHORT_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH

APPOINTMENT_STATUSES = ["pianificato", "completato", "annullato"]


class AppointmentIn(BaseModel):
    client_id: Optional[str] = None
    title: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    description: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    start: str
    end: Optional[str] = None
    location: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    status: Literal[*APPOINTMENT_STATUSES] = "pianificato"


class AppointmentBulkIn(BaseModel):
    """Creazione in blocco, usata dal pianificatore giro visite per salvare
    tutte le tappe calcolate come appuntamenti in un'unica richiesta. Stesso
    tetto del numero massimo di clienti del pianificatore (MAX_ROUTE_CLIENTS),
    per lo stesso motivo: evitare un numero enorme di push verso Google
    Calendar in un colpo solo."""
    appointments: List[AppointmentIn] = Field(..., min_length=1, max_length=50)
