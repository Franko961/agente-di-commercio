from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from models.order import SALE_TYPES
from core.validation_limits import (
    SHORT_TEXT_MAX_LENGTH, MEDIUM_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH,
    MAX_QUANTITY, MAX_UNIT_PRICE, MAX_LINE_ITEMS,
)

OFFER_STATUSES = ["bozza", "inviata", "accettata", "rifiutata", "scaduta"]


class OfferLineItem(BaseModel):
    product_id: Optional[str] = None
    description: str = Field(max_length=MEDIUM_TEXT_MAX_LENGTH)
    # Limiti che evitano un totale riga negativo o assurdo, che si
    # propagherebbe al totale dell'offerta e da lì alla provvigione
    # calcolata su di esso (services.commission_service.calc_offer_total):
    # una quantità <= 0, un prezzo negativo, o uno sconto oltre il 100%
    # produrrebbero un sub-totale negativo senza che nulla lo impedisse. I
    # tetti massimi (vedi core/validation_limits.py) sono guardrail contro
    # un valore inserito con uno zero di troppo, non un vincolo di business.
    quantity: float = Field(1, gt=0, le=MAX_QUANTITY)
    unit_price: float = Field(0.0, ge=0, le=MAX_UNIT_PRICE)
    discount: float = Field(0.0, ge=0, le=100)


class OfferIn(BaseModel):
    client_id: str
    mandante_id: str
    title: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    items: List[OfferLineItem] = Field(default_factory=list, max_length=MAX_LINE_ITEMS)
    expires_at: Optional[str] = None
    status: Literal[*OFFER_STATUSES] = "bozza"
    sale_type: Literal[*SALE_TYPES] = "nuovo"
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)


class OfferStatusIn(BaseModel):
    status: Literal[*OFFER_STATUSES]


class SignatureIn(BaseModel):
    signature: str  # base64 PNG data URL
    signer_name: Optional[str] = ""
