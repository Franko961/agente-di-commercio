from pydantic import BaseModel, Field
from typing import List, Optional


class OfferLineItem(BaseModel):
    product_id: Optional[str] = None
    description: str
    # Limiti che evitano un totale riga negativo o assurdo, che si
    # propagherebbe al totale dell'offerta e da lì alla provvigione
    # calcolata su di esso (services.commission_service.calc_offer_total):
    # una quantità <= 0, un prezzo negativo, o uno sconto oltre il 100%
    # produrrebbero un sub-totale negativo senza che nulla lo impedisse.
    quantity: float = Field(1, gt=0)
    unit_price: float = Field(0.0, ge=0)
    discount: float = Field(0.0, ge=0, le=100)


class OfferIn(BaseModel):
    client_id: str
    mandante_id: str
    title: str
    items: List[OfferLineItem] = []
    expires_at: Optional[str] = None
    status: str = "bozza"  # bozza, inviata, accettata, rifiutata, scaduta
    sale_type: str = "nuovo"  # nuovo, rinnovo — determina l'aliquota di provvigione applicata
    notes: Optional[str] = ""


class SignatureIn(BaseModel):
    signature: str  # base64 PNG data URL
    signer_name: Optional[str] = ""
