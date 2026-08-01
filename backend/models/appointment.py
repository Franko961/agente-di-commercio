from pydantic import BaseModel, Field
from typing import List, Literal, Optional

APPOINTMENT_STATUSES = ["pianificato", "completato", "annullato"]


class AppointmentIn(BaseModel):
    client_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    start: str
    end: Optional[str] = None
    location: Optional[str] = ""
    status: Literal[*APPOINTMENT_STATUSES] = "pianificato"


class AppointmentBulkIn(BaseModel):
    """Creazione in blocco, usata dal pianificatore giro visite per salvare
    tutte le tappe calcolate come appuntamenti in un'unica richiesta. Stesso
    tetto del numero massimo di clienti del pianificatore (MAX_ROUTE_CLIENTS),
    per lo stesso motivo: evitare un numero enorme di push verso Google
    Calendar in un colpo solo."""
    appointments: List[AppointmentIn] = Field(..., min_length=1, max_length=50)
