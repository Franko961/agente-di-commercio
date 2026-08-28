"""
Verifica create_document_download_token/decode_document_download_token
(core/security.py): il meccanismo che sostituisce il vecchio
?auth=<token di sessione completo> nell'URL di download documenti.

Il token generato deve:
- essere valido solo per il documento per cui è stato emesso;
- scadere dopo pochi minuti (DOCUMENT_DOWNLOAD_TOKEN_TTL_MINUTES);
- essere rifiutato se qualcuno tenta di riusare un token di scopo diverso
  (es. un token di reset password o di altra natura) su questo endpoint.

Puramente logico, nessuna dipendenza da DB/rete: esegui con
    JWT_SECRET=test python -m pytest tests/test_document_download_token.py -v
"""

import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest

sys.path.insert(0, ".")

from core.config import JWT_ALG, JWT_SECRET
from core.security import (
    DOCUMENT_DOWNLOAD_TOKEN_TTL_MINUTES,
    create_document_download_token,
    decode_document_download_token,
)


def test_token_valido_per_il_proprio_documento():
    token = create_document_download_token("user-1", "doc-1")
    user_id = decode_document_download_token(token, "doc-1")
    assert user_id == "user-1"


def test_token_rifiutato_per_un_documento_diverso():
    token = create_document_download_token("user-1", "doc-1")
    with pytest.raises(jwt.InvalidTokenError):
        decode_document_download_token(token, "doc-2")


def test_token_scaduto_viene_rifiutato():
    expired_payload = {
        "sub": "user-1",
        "doc_id": "doc-1",
        "purpose": "doc_download",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALG)
    with pytest.raises(jwt.InvalidTokenError):
        decode_document_download_token(expired_token, "doc-1")


def test_token_con_scopo_diverso_viene_rifiutato():
    """Un token firmato valido ma emesso per un altro scopo (es. reset
    password) non deve poter essere riusato per scaricare un documento —
    anche se la firma è corretta e non è scaduto."""
    other_purpose_payload = {
        "sub": "user-1",
        "doc_id": "doc-1",
        "purpose": "reset_password",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(other_purpose_payload, JWT_SECRET, algorithm=JWT_ALG)
    with pytest.raises(jwt.InvalidTokenError):
        decode_document_download_token(token, "doc-1")


def test_token_manomesso_viene_rifiutato():
    token = create_document_download_token("user-1", "doc-1")
    # Manomette un carattere a metà del token, non l'ultimo: l'ultimo
    # carattere di un gruppo base64 può codificare bit non significativi
    # (padding), quindi alterarlo a volte non cambia il valore decodificato
    # e il test risulterebbe intermittente. Un carattere a metà stringa
    # cade quasi certamente dentro la firma o il payload in un punto che
    # ne altera davvero il contenuto, indipendentemente dalla lunghezza
    # esatta del token generato in questo run.
    mid = len(token) // 2
    tampered = token[:mid] + ("A" if token[mid] != "A" else "B") + token[mid + 1 :]
    with pytest.raises(jwt.InvalidTokenError):
        decode_document_download_token(tampered, "doc-1")


def test_ttl_e_ragionevolmente_breve():
    """Non un test sul valore esatto, ma sulla proprietà che conta: il
    link deve scadere in minuti, non in giorni come il token di sessione."""
    assert DOCUMENT_DOWNLOAD_TOKEN_TTL_MINUTES <= 30


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
