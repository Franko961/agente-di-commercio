from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from core.validation_limits import SHORT_TEXT_MAX_LENGTH

# bcrypt (usato in core/security.py per l'hashing) tronca silenziosamente
# la password oltre i 72 byte: senza un limite qui, un utente potrebbe
# "impostare" una password di 200 caratteri credendo che conti per intero,
# mentre in realtà solo i primi 72 byte determinano l'hash — due password
# diverse che condividono lo stesso prefisso di 72 byte risulterebbero
# indistinguibili per bcrypt. Applicato solo dove una password viene
# IMPOSTATA (registrazione, reset), non al login: lì bcrypt.checkpw
# applica la stessa troncatura in modo coerente, quindi non c'è nulla da
# correggere su quel campo.
PASSWORD_MAX_LENGTH = 72


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)
    name: str = Field(max_length=SHORT_TEXT_MAX_LENGTH)
    plan: Optional[str] = "base"  # 'base' o 'pro'


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(max_length=PASSWORD_MAX_LENGTH)
