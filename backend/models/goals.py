from pydantic import BaseModel, Field
from typing import Optional
from core.validation_limits import MAX_MONETARY_TARGET, MAX_COUNT


class GoalsIn(BaseModel):
    """Obiettivi mensili configurabili dall'utente. Tutti opzionali: un campo
    lasciato a None significa "non impostato", non "obiettivo zero" — nel
    resto dell'app questo si traduce in "nessuna percentuale calcolata per
    questa metrica" invece di un fuorviante 0/0 = 100%."""
    goal_revenue: Optional[float] = Field(None, ge=0, le=MAX_MONETARY_TARGET)
    goal_commissions: Optional[float] = Field(None, ge=0, le=MAX_MONETARY_TARGET)
    goal_new_clients: Optional[int] = Field(None, ge=0, le=MAX_COUNT)
    goal_visits: Optional[int] = Field(None, ge=0, le=MAX_COUNT)
