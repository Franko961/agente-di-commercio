"""
Cifratura simmetrica per dati sensibili salvati a riposo nel DB
(es. refresh token di Google Calendar).

La chiave Fernet viene derivata deterministicamente da JWT_SECRET tramite SHA-256,
così non serve gestire un'ulteriore variabile d'ambiente segreta su Railway:
JWT_SECRET è già obbligatoria e già trattata come segreto critico.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from core.config import JWT_SECRET

_key = base64.urlsafe_b64encode(hashlib.sha256(JWT_SECRET.encode("utf-8")).digest())
_fernet = Fernet(_key)


def encrypt_str(plain: str) -> str:
    return _fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_str(token: str) -> str:
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("Token cifrato non valido o chiave cambiata")
