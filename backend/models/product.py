from typing import List, Optional

from pydantic import BaseModel, Field

from core.validation_limits import (
    MAX_BULK_IMPORT_ITEMS,
    MAX_UNIT_PRICE,
    SHORT_TEXT_MAX_LENGTH,
)


class ProductIn(BaseModel):
    mandante_id: str
    name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    sku: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    # Un prezzo/costo negativo si propagherebbe a qualunque offerta/ordine
    # che riusi questo prodotto per precompilare la riga (stesso rischio già
    # sistemato su OfferLineItem/OrderLineItem in models/offer.py e
    # models/order.py). Il tetto massimo è lo stesso guardrail di quei
    # campi, non un vincolo di business.
    price: float = Field(ge=0, le=MAX_UNIT_PRICE)
    cost: Optional[float] = Field(0.0, ge=0, le=MAX_UNIT_PRICE)
    commission_rate: Optional[float] = Field(
        None, ge=0, le=100
    )  # override mandante if set
    category: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)


class ProductBulkItem(BaseModel):
    """Un prodotto da importare in blocco (es. da un listino fornitore in
    PDF/Excel): stessi campi di ProductIn ma senza mandante_id, risolto una
    sola volta a livello di richiesta tramite mandante_name."""

    sku: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    price: float = Field(ge=0, le=MAX_UNIT_PRICE)
    cost: Optional[float] = Field(0.0, ge=0, le=MAX_UNIT_PRICE)
    commission_rate: Optional[float] = Field(None, ge=0, le=100)
    category: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)


class ProductBulkIn(BaseModel):
    mandante_name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    products: List[ProductBulkItem] = Field(..., max_length=MAX_BULK_IMPORT_ITEMS)
