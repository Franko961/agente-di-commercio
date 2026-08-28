from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from core.validation_limits import SHORT_TEXT_MAX_LENGTH


class DemoRequestIn(BaseModel):
    nome: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    cognome: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    email: EmailStr
    azienda: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    telefono: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    privacy_consent: bool = False
    marketing_consent: bool = False
