from typing import Optional

from pydantic import BaseModel


class AddressesIn(BaseModel):
    """Indirizzi di casa/ufficio dell'agente, usati come possibile punto di
    partenza nel pianificatore visite. Tutti opzionali e indipendenti: si può
    impostare solo casa, solo ufficio, o nessuno dei due (in quel caso quelle
    due opzioni restano semplicemente non selezionabili nel pianificatore)."""

    home_address: Optional[str] = None
    home_lat: Optional[float] = None
    home_lng: Optional[float] = None
    office_address: Optional[str] = None
    office_lat: Optional[float] = None
    office_lng: Optional[float] = None
