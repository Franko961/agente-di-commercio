from pydantic import BaseModel, Field
from typing import Literal, Optional
from core.validation_limits import SHORT_TEXT_MAX_LENGTH, LONG_TEXT_MAX_LENGTH

EMPLOYEE_DOCUMENT_CATEGORIES = ("contratto", "documento_identita", "patente", "contestazione_disciplinare", "altro")


class EmployeeDocumentMetaUpdate(BaseModel):
    """Aggiornamento mirato dei metadati (senza ricaricare il file), stesso
    schema "patch" di DocumentMetaUpdate (models/document.py)."""
    name: Optional[str] = Field(None, max_length=SHORT_TEXT_MAX_LENGTH)
    category: Optional[Literal[*EMPLOYEE_DOCUMENT_CATEGORIES]] = None
    notes: Optional[str] = Field(None, max_length=LONG_TEXT_MAX_LENGTH)
