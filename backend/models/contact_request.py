from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from core.validation_limits import LONG_TEXT_MAX_LENGTH, SHORT_TEXT_MAX_LENGTH


class ContactRequestIn(BaseModel):
    nome: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    email: EmailStr
    telefono: Optional[str] = Field("", max_length=SHORT_TEXT_MAX_LENGTH)
    messaggio: str = Field(max_length=LONG_TEXT_MAX_LENGTH)
    privacy_consent: bool = False
