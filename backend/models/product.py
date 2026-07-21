from pydantic import BaseModel
from typing import List, Optional


class ProductIn(BaseModel):
    mandante_id: str
    name: str
    sku: Optional[str] = ""
    price: float
    cost: Optional[float] = 0.0
    commission_rate: Optional[float] = None  # override mandante if set
    category: Optional[str] = ""


class ProductBulkItem(BaseModel):
    """Un prodotto da importare in blocco (es. da un listino fornitore in
    PDF/Excel): stessi campi di ProductIn ma senza mandante_id, risolto una
    sola volta a livello di richiesta tramite mandante_name."""
    sku: str
    name: str
    price: float
    cost: Optional[float] = 0.0
    commission_rate: Optional[float] = None
    category: Optional[str] = ""


class ProductBulkIn(BaseModel):
    mandante_name: str
    products: List[ProductBulkItem]
