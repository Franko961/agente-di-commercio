from typing import List, Optional

from pydantic import BaseModel, Field

from core.validation_limits import (
    LONG_TEXT_MAX_LENGTH,
    MAX_BULK_IMPORT_ITEMS,
    MAX_MANDANTI_PER_CLIENT,
    MEDIUM_TEXT_MAX_LENGTH,
    SHORT_TEXT_MAX_LENGTH,
)


class ClientIn(BaseModel):
    company_name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    contact_name: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    email: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    phone: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    vat_number: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    address: Optional[str] = Field("", max_length=MEDIUM_TEXT_MAX_LENGTH)
    city: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    province: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    zone: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    sector: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    potential: Optional[str] = "medio"
    # Limiti geografici reali (-90/90, -180/180): senza questo vincolo, una
    # coordinata corrotta (es. lat/lng invertite da un match di geocodifica
    # sbagliato) poteva essere salvata e poi mandare in crash "Out of
    # Memory" il browser quando Leaflet provava a renderla su una mappa a
    # zoom alto (vedi LocationPicker.jsx/MapView.jsx).
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    mandante_ids: List[str] = Field(
        default_factory=list, max_length=MAX_MANDANTI_PER_CLIENT
    )
    birthday: Optional[str] = (
        None  # data di nascita, formato "YYYY-MM-DD" (facoltativa)
    )


class ClientBulkItem(BaseModel):
    """Un cliente da importare in blocco da un file caricato direttamente
    dall'utente (CSV/Excel) — stessi campi di ClientIn, ma con mandante
    indicato per nome (risolto lato server, come già avviene per il listino
    prodotti) invece che per id, dato che nel file l'utente scrive il nome
    del mandante, non conosce gli id interni."""

    company_name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    contact_name: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    email: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    phone: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    vat_number: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    address: Optional[str] = Field("", max_length=MEDIUM_TEXT_MAX_LENGTH)
    city: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    province: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    zone: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    sector: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    potential: Optional[str] = "medio"
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    mandante_names: Optional[str] = Field(
        "", max_length=MEDIUM_TEXT_MAX_LENGTH
    )  # nomi separati da virgola/punto e virgola, es. "Rossi Spa; Bianchi Srl"


class ClientBulkIn(BaseModel):
    clients: List[ClientBulkItem] = Field(..., max_length=MAX_BULK_IMPORT_ITEMS)
