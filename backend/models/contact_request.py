from pydantic import BaseModel, EmailStr
from typing import Optional


class ContactRequestIn(BaseModel):
    nome: str
    email: EmailStr
    telefono: Optional[str] = ""
    messaggio: str
    privacy_consent: bool = False
