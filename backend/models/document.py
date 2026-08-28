from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from core.validation_limits import (
    LONG_TEXT_MAX_LENGTH,
    MAX_TAGS,
    MEDIUM_TEXT_MAX_LENGTH,
    SHORT_TEXT_MAX_LENGTH,
)

# Allineata alle opzioni reali del menu a tendina nel frontend
# (frontend/src/pages/Documents.jsx) — il vecchio commento qui elencava solo
# "contratto, offerta, fattura, altro", disallineato da tempo: mancavano
# "listino", "scontrino" e "video", già in uso.
DOCUMENT_CATEGORIES = [
    "contratto",
    "offerta",
    "fattura",
    "listino",
    "scontrino",
    "video",
    "altro",
]


class DocumentIn(BaseModel):
    client_id: Optional[str] = None
    name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    category: Literal[*DOCUMENT_CATEGORIES] = "contratto"
    url: Optional[str] = Field("", max_length=MEDIUM_TEXT_MAX_LENGTH)
    notes: Optional[str] = Field("", max_length=LONG_TEXT_MAX_LENGTH)
    tags: List[str] = Field(default_factory=list, max_length=MAX_TAGS)


class DocumentMetaUpdate(BaseModel):
    """Aggiornamento mirato dei metadati (senza ricaricare il file). Tutti i
    campi opzionali: solo quelli presenti nella richiesta vengono
    aggiornati (semantica "patch", vedi document_service.update_document_meta)."""

    name: Optional[str] = Field(None, max_length=SHORT_TEXT_MAX_LENGTH)
    category: Optional[Literal[*DOCUMENT_CATEGORIES]] = None
    notes: Optional[str] = Field(None, max_length=LONG_TEXT_MAX_LENGTH)
    client_id: Optional[str] = None
    tags: Optional[List[str]] = Field(None, max_length=MAX_TAGS)
