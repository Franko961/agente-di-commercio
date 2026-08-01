from pydantic import BaseModel, Field
from typing import List, Optional
from core.validation_limits import (
    SHORT_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH, MAX_MONETARY_TARGET, MAX_COUNT,
)

MAX_BONUS_TIERS = 20  # scaglioni premio configurabili per mandante


class BonusTier(BaseModel):
    threshold: float = Field(ge=0, le=MAX_MONETARY_TARGET)  # fatturato minimo per ottenere il bonus
    bonus: float = Field(ge=0, le=MAX_MONETARY_TARGET)      # importo premio


class MandanteIn(BaseModel):
    name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    brand_color: Optional[str] = "#0A192F"
    # Aliquote percentuali: senza questi limiti un valore negativo o oltre
    # il 100% (es. inserito per errore) produrrebbe una provvigione
    # negativa o assurda in tutti i calcoli che la usano (vedi
    # services.commission_service.get_commission_rate).
    commission_rate: float = Field(5.0, ge=0, le=100)
    commission_rate_new: Optional[float] = Field(None, ge=0, le=100)      # override su vendite nuove, se impostato
    commission_rate_renewal: Optional[float] = Field(None, ge=0, le=100)  # override su rinnovi, se impostato
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    # Prima senza alcun limite, nemmeno inferiore: un obiettivo negativo o
    # assurdo restava salvato così com'è (modificabile dalla pagina Mandanti).
    target_monthly: Optional[float] = Field(None, ge=0, le=MAX_MONETARY_TARGET)
    target_yearly: Optional[float] = Field(None, ge=0, le=MAX_MONETARY_TARGET)
    target_clients: Optional[int] = Field(None, ge=0, le=MAX_COUNT)
    target_notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    bonus_tiers: Optional[List[BonusTier]] = Field(default_factory=list, max_length=MAX_BONUS_TIERS)
