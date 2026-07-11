from pydantic import BaseModel
from typing import List, Optional


class OfferLineItem(BaseModel):
    product_id: Optional[str] = None
    description: str
    quantity: float = 1
    unit_price: float = 0.0
    discount: float = 0.0


class OfferIn(BaseModel):
    client_id: str
    mandante_id: str
    title: str
    items: List[OfferLineItem] = []
    expires_at: Optional[str] = None
    status: str = "bozza"  # bozza, inviata, accettata, rifiutata, scaduta
    sale_type: str = "nuovo"  # nuovo, rinnovo — determina l'aliquota di provvigione applicata
    notes: Optional[str] = ""
