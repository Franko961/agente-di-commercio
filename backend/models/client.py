from pydantic import BaseModel, Field
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
    # Limiti geografici reali (-90/90, -180/180): senza questo vincolo, una
    # coordinata corrotta (es. lat/lng invertite da un match di geocodifica
    # sbagliato) poteva essere salvata e poi mandare in crash "Out of
    # Memory" il browser quando Leaflet provava a renderla su una mappa a
    # zoom alto (vedi LocationPicker.jsx/MapView.jsx).
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    notes: Optional[str] = ""
    mandante_ids: List[str] = Field(default_factory=list)
    birthday: Optional[str] = None  # data di nascita, formato "YYYY-MM-DD" (facoltativa)


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
