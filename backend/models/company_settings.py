from typing import Optional

from pydantic import BaseModel, Field

from core.validation_limits import PHOTO_MAX_LENGTH


class CompanySettingsIn(BaseModel):
    """Logo aziendale mostrato in testa all'export cartellino (vedi
    services/attendance_xlsx_export.py) — data URL base64, stessa forma e
    stesso limite già usati per la foto profilo del dipendente
    (models/employee.py): va ridimensionato/compresso lato client prima
    dell'invio. Opzionale: senza logo l'export si genera comunque, solo
    senza l'immagine in testa.

    vat_number: Partita IVA dell'agente, mostrata in testa al report PDF
    provvigioni per mandante (vedi services/mandante_report_service.py) —
    stesso principio del logo: opzionale, senza il report si genera
    comunque, solo senza quella riga in intestazione."""

    logo: Optional[str] = Field(None, max_length=PHOTO_MAX_LENGTH)
    vat_number: Optional[str] = Field(None, max_length=20)
