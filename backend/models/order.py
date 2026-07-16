from pydantic import BaseModel
from typing import List, Optional


class OrderLineItem(BaseModel):
    product_id: Optional[str] = None
    description: str
    quantity: float = 1
    unit_price: float = 0.0
    discount: float = 0.0


class OrderIn(BaseModel):
    client_id: str
    mandante_id: str
    items: List[OrderLineItem] = []
    sale_type: str = "nuovo"  # nuovo, rinnovo — determina l'aliquota di provvigione applicata
    notes: Optional[str] = ""
