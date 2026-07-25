from pydantic import BaseModel, Field
from typing import Optional


class GoalsIn(BaseModel):
    """Obiettivi mensili configurabili dall'utente. Tutti opzionali: un campo
    lasciato a None significa "non impostato", non "obiettivo zero" — nel
    resto dell'app questo si traduce in "nessuna percentuale calcolata per
    questa metrica" invece di un fuorviante 0/0 = 100%."""
    goal_revenue: Optional[float] = Field(None, ge=0)
    goal_commissions: Optional[float] = Field(None, ge=0)
    goal_new_clients: Optional[int] = Field(None, ge=0)
    goal_visits: Optional[int] = Field(None, ge=0)
