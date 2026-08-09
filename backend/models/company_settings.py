from pydantic import BaseModel, Field
from typing import Optional
from core.validation_limits import PHOTO_MAX_LENGTH


class CompanySettingsIn(BaseModel):
    """Logo aziendale mostrato in testa all'export cartellino (vedi
    services/attendance_xlsx_export.py) — data URL base64, stessa forma e
    stesso limite già usati per la foto profilo del dipendente
    (models/employee.py): va ridimensionato/compresso lato client prima
    dell'invio. Opzionale: senza logo l'export si genera comunque, solo
    senza l'immagine in testa."""
    logo: Optional[str] = Field(None, max_length=PHOTO_MAX_LENGTH)
