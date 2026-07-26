from pydantic import BaseModel, Field
from typing import List


class RoutePlanIn(BaseModel):
    client_ids: List[str] = Field(..., min_length=1)
    start_time: str = "09:00"  # formato HH:MM, ora locale dell'agente
    visit_minutes: int = 30  # durata assunta per ogni visita, usata per calcolare gli orari proposti
