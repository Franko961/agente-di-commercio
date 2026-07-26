from pydantic import BaseModel, Field
from typing import List, Optional

# Stato del ciclo di vita dell'ordine. "annullato"/"reso" sono gli unici due
# stati che comportano la rimozione della provvigione collegata (vedi
# order_service.update_order_status) — gli altri sono solo informativi.
ORDER_STATUSES = ["confermato", "in_evasione", "spedito", "consegnato", "annullato", "reso"]
PAYMENT_STATUSES = ["non_pagato", "parziale", "pagato"]


class OrderLineItem(BaseModel):
    product_id: Optional[str] = None
    description: str
    # Stessi limiti di OfferLineItem (models/offer.py): evitano un
    # sub-totale riga negativo che si propagherebbe al totale ordine e da
    # lì alla provvigione calcolata su di esso.
    quantity: float = Field(1, gt=0)
    unit_price: float = Field(0.0, ge=0)
    discount: float = Field(0.0, ge=0, le=100)


class OrderIn(BaseModel):
    client_id: str
    mandante_id: str
    items: List[OrderLineItem] = []
    sale_type: str = "nuovo"  # nuovo, rinnovo — determina l'aliquota di provvigione applicata
    notes: Optional[str] = ""
    numero_ordine: Optional[str] = None  # se omesso, generato automaticamente alla creazione
    status: str = "confermato"
    payment_status: str = "non_pagato"
    expected_delivery_date: Optional[str] = None  # data prevista di consegna (YYYY-MM-DD)
    delivery_date: Optional[str] = None  # data di consegna effettiva


class OrderStatusIn(BaseModel):
    """Aggiornamento mirato di stato/evasione/pagamento, senza dover
    rimandare l'intero ordine (righe, prezzi, ecc.) come richiederebbe PUT.
    Tutti i campi opzionali: solo quelli presenti nella richiesta vengono
    aggiornati (semantica "patch", non "replace")."""
    status: Optional[str] = None
    payment_status: Optional[str] = None
    numero_ordine: Optional[str] = None
    expected_delivery_date: Optional[str] = None
    delivery_date: Optional[str] = None
