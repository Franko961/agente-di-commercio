"""
Verifica core.security.set_auth_cookie/clear_auth_cookie: il cookie di
sessione deve avere SameSite=Lax (non "none"), perché il frontend chiama
sempre /api/* con URL relativo — in produzione quel percorso passa dal
proxy Netlify verso Railway (frontend/public/_redirects), quindi dal punto
di vista del browser la richiesta è sempre same-site. SameSite=None
richiederebbe una vera protezione CSRF, assente oggi, per una proprietà
che l'architettura attuale non sfrutta comunque.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_auth_cookie_samesite.py -v
"""

import sys

sys.path.insert(0, ".")

from fastapi import Response

from core.security import ACCESS_TOKEN_TTL_SECONDS, clear_auth_cookie, set_auth_cookie


def _set_cookie_header(response: Response) -> str:
    return response.headers.get("set-cookie", "")


def test_set_auth_cookie_usa_samesite_lax():
    response = Response()
    set_auth_cookie(response, "un-token-finto")

    header = _set_cookie_header(response)
    assert "samesite=lax" in header.lower()
    assert "httponly" in header.lower()
    assert "secure" in header.lower()
    assert "access_token=un-token-finto" in header


def test_set_auth_cookie_usa_ttl_di_default_a_7_giorni():
    response = Response()
    set_auth_cookie(response, "un-token-finto")

    header = _set_cookie_header(response)
    assert f"max-age={ACCESS_TOKEN_TTL_SECONDS}" in header.lower()


def test_set_auth_cookie_accetta_un_max_age_diverso():
    """Usato da POST /api/admin/users/{uid}/impersonate con la TTL più
    breve dell'impersonificazione, non i 7 giorni del login normale."""
    response = Response()
    set_auth_cookie(response, "un-token-finto", max_age=3600)

    header = _set_cookie_header(response)
    assert "max-age=3600" in header.lower()


def test_clear_auth_cookie_usa_samesite_lax():
    response = Response()
    clear_auth_cookie(response)

    header = _set_cookie_header(response)
    assert "samesite=lax" in header.lower()
    # delete_cookie scade il cookie svuotandolo, non deve più contenere un token
    assert (
        'access_token=""' in header
        or "access_token=;" in header
        or 'access_token="";' in header
    )


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
