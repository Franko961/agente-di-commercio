from pydantic import BaseModel
from typing import List, Optional

class ClientIn(BaseModel):
    company_name: str
    contact_name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    vat_number: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    province: Optional[str] = ""
    zone: Optional[str] = ""
    sector: Optional[str] = ""
    potential: Optional[str] = "medio"
    lat: Optional[float] = None
    lng: Optional[float] = None
    notes: Optional[str] = ""
    mandante_ids: List[str] = []


class ClientBulkItem(BaseModel):
    """Un cliente da importare in blocco da un file caricato direttamente
    dall'utente (CSV/Excel) — stessi campi di ClientIn, ma con mandante
    indicato per nome (risolto lato server, come già avviene per il listino
    prodotti) invece che per id, dato che nel file l'utente scrive il nome
    del mandante, non conosce gli id interni."""
    company_name: str
    contact_name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    vat_number: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    province: Optional[str] = ""
    zone: Optional[str] = ""
    sector: Optional[str] = ""
    potential: Optional[str] = "medio"
    notes: Optional[str] = ""
    mandante_names: Optional[str] = ""  # nomi separati da virgola/punto e virgola, es. "Rossi Spa; Bianchi Srl"


class ClientBulkIn(BaseModel):
    clients: List[ClientBulkItem]
