from pydantic import BaseModel, Field
from typing import List, Optional


class ProductIn(BaseModel):
    mandante_id: str
    name: str
    sku: Optional[str] = ""
    # Un prezzo/costo negativo si propagherebbe a qualunque offerta/ordine
    # che riusi questo prodotto per precompilare la riga (stesso rischio già
    # sistemato su OfferLineItem/OrderLineItem in models/offer.py e
    # models/order.py).
    price: float = Field(ge=0)
    cost: Optional[float] = Field(0.0, ge=0)
    commission_rate: Optional[float] = Field(None, ge=0, le=100)  # override mandante if set
    category: Optional[str] = ""


class ProductBulkItem(BaseModel):
    """Un prodotto da importare in blocco (es. da un listino fornitore in
    PDF/Excel): stessi campi di ProductIn ma senza mandante_id, risolto una
    sola volta a livello di richiesta tramite mandante_name."""
    sku: str
    name: str
    price: float = Field(ge=0)
    cost: Optional[float] = Field(0.0, ge=0)
    commission_rate: Optional[float] = Field(None, ge=0, le=100)
    category: Optional[str] = ""


class ProductBulkIn(BaseModel):
    mandante_name: str
    products: List[ProductBulkItem]
