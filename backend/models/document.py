from pydantic import BaseModel
from typing import List, Literal, Optional

# Allineata alle opzioni reali del menu a tendina nel frontend
# (frontend/src/pages/Documents.jsx) — il vecchio commento qui elencava solo
# "contratto, offerta, fattura, altro", disallineato da tempo: mancavano
# "listino", "scontrino" e "video", già in uso.
DOCUMENT_CATEGORIES = ["contratto", "offerta", "fattura", "listino", "scontrino", "video", "altro"]


class DocumentIn(BaseModel):
    client_id: Optional[str] = None
    name: str
    category: Literal[*DOCUMENT_CATEGORIES] = "contratto"
    url: Optional[str] = ""
    notes: Optional[str] = ""
    tags: List[str] = []


class DocumentMetaUpdate(BaseModel):
    """Aggiornamento mirato dei metadati (senza ricaricare il file). Tutti i
    campi opzionali: solo quelli presenti nella richiesta vengono
    aggiornati (semantica "patch", vedi document_service.update_document_meta)."""
    name: Optional[str] = None
    category: Optional[Literal[*DOCUMENT_CATEGORIES]] = None
    notes: Optional[str] = None
    client_id: Optional[str] = None
    tags: Optional[List[str]] = None
