from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# Stato del ciclo di vita dell'ordine. "annullato"/"reso" sono gli unici due
# stati che comportano la rimozione della provvigione collegata (vedi
# order_service.update_order_status) — gli altri sono solo informativi.
ORDER_STATUSES = ["confermato", "in_evasione", "spedito", "consegnato", "annullato", "reso"]
PAYMENT_STATUSES = ["non_pagato", "parziale", "pagato"]
# Condiviso con models/offer.py (importato da lì, non duplicato): determina
# quale aliquota di provvigione del mandante viene applicata (vedi
# services/commission_service.get_commission_rate) — un valore fuori da
# questi due sarebbe silenziosamente ignorato da entrambi i rami di quella
# funzione, risultando nella provvigione di default invece che in un errore.
SALE_TYPES = ["nuovo", "rinnovo"]


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
    sale_type: Literal[*SALE_TYPES] = "nuovo"
    notes: Optional[str] = ""
    numero_ordine: Optional[str] = None  # se omesso, generato automaticamente alla creazione
    status: Literal[*ORDER_STATUSES] = "confermato"
    payment_status: Literal[*PAYMENT_STATUSES] = "non_pagato"
    expected_delivery_date: Optional[str] = None  # data prevista di consegna (YYYY-MM-DD)
    delivery_date: Optional[str] = None  # data di consegna effettiva


class OrderStatusIn(BaseModel):
    """Aggiornamento mirato di stato/evasione/pagamento, senza dover
    rimandare l'intero ordine (righe, prezzi, ecc.) come richiederebbe PUT.
    Tutti i campi opzionali: solo quelli presenti nella richiesta vengono
    aggiornati (semantica "patch", non "replace")."""
    status: Optional[Literal[*ORDER_STATUSES]] = None
    payment_status: Optional[Literal[*PAYMENT_STATUSES]] = None
    numero_ordine: Optional[str] = None
    expected_delivery_date: Optional[str] = None
    delivery_date: Optional[str] = None
