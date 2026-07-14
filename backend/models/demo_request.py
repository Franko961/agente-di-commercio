from pydantic import BaseModel, EmailStr
from typing import Optional


class DemoRequestIn(BaseModel):
    nome: str
    cognome: str
    email: EmailStr
    azienda: Optional[str] = ""
    telefono: Optional[str] = ""
    privacy_consent: bool = False
    marketing_consent: bool = False
