from pydantic import BaseModel, Field
from typing import List, Optional


class BonusTier(BaseModel):
    threshold: float = Field(ge=0)  # fatturato minimo per ottenere il bonus
    bonus: float = Field(ge=0)      # importo premio


class MandanteIn(BaseModel):
    name: str
    brand_color: Optional[str] = "#0A192F"
    # Aliquote percentuali: senza questi limiti un valore negativo o oltre
    # il 100% (es. inserito per errore) produrrebbe una provvigione
    # negativa o assurda in tutti i calcoli che la usano (vedi
    # services.commission_service.get_commission_rate).
    commission_rate: float = Field(5.0, ge=0, le=100)
    commission_rate_new: Optional[float] = Field(None, ge=0, le=100)      # override su vendite nuove, se impostato
    commission_rate_renewal: Optional[float] = Field(None, ge=0, le=100)  # override su rinnovi, se impostato
    notes: Optional[str] = ""
    target_monthly: Optional[float] = None
    target_yearly: Optional[float] = None
    target_clients: Optional[int] = None
    target_notes: Optional[str] = ""
    bonus_tiers: Optional[List[BonusTier]] = []
