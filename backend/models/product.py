from pydantic import BaseModel
from typing import Optional


class ProductIn(BaseModel):
    mandante_id: str
    name: str
    sku: Optional[str] = ""
    price: float
    cost: Optional[float] = 0.0
    commission_rate: Optional[float] = None  # override mandante if set
    category: Optional[str] = ""
