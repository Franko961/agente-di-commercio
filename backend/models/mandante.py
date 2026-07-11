from pydantic import BaseModel
from typing import List, Optional


class BonusTier(BaseModel):
    threshold: float   # fatturato minimo per ottenere il bonus
    bonus: float        # importo premio


class MandanteIn(BaseModel):
    name: str
    brand_color: Optional[str] = "#0A192F"
    commission_rate: float = 5.0
    commission_rate_new: Optional[float] = None      # override su vendite nuove, se impostato
    commission_rate_renewal: Optional[float] = None  # override su rinnovi, se impostato
    notes: Optional[str] = ""
    target_monthly: Optional[float] = None
    target_yearly: Optional[float] = None
    target_clients: Optional[int] = None
    target_notes: Optional[str] = ""
    bonus_tiers: Optional[List[BonusTier]] = []
