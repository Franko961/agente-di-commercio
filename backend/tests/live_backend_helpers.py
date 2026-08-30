"""Helper condivisi dai file di test che parlano HTTP con un backend
realmente in esecuzione (test_backend_api.py, test_documents_iter6.py,
test_documents_upload.py, test_p1_features.py).

MAI più loggarsi sull'account demo pubblico condiviso (agente@demo.it):
quell'account ha is_demo=True, e forbid_demo_write (core/security.py)
blocca con 403 QUALUNQUE scrittura per un account demo — i test di
create/update/delete non potrebbero mai passare contro di esso,
indipendentemente da come si legge il token. Ogni funzione qui registra
invece un account dedicato e fresco, seminato automaticamente con dati CRM
coerenti da services/seed_service.py (lo stesso seed usato per gli account
demo) — da cui gli assert "almeno N clienti/lead/offerte" in questi test.
"""

import os
import uuid
from typing import Optional

import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000").rstrip("/")
API = f"{BASE_URL}/api"
PASSWORD = "TestLiveBackend2026!"


def register_live_backend_account(name: str) -> Optional[dict]:
    """Registra un account dedicato (email univoca) su un backend realmente
    in esecuzione. Ritorna {email, password, token} — il token è letto dal
    cookie Set-Cookie della risposta (core/security.py::set_auth_cookie),
    mai dal body: login/registrazione non restituiscono più un token nel
    JSON da quando l'autenticazione è passata a cookie httpOnly.

    Ritorna None se il backend non è raggiungibile o la registrazione
    fallisce — il fixture chiamante lo trasforma in pytest.skip(), non un
    errore (stesso comportamento di prima per chi lancia pytest senza un
    backend locale attivo)."""
    email = f"test-{name}-{uuid.uuid4().hex[:10]}@example.com"
    try:
        r = requests.post(
            f"{API}/auth/register",
            json={"email": email, "password": PASSWORD, "name": f"Test {name}"},
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        return None
    if r.status_code != 200:
        return None
    token = r.cookies.get("access_token")
    if not token:
        return None
    return {"email": email, "password": PASSWORD, "token": token}


def delete_live_backend_account(account: Optional[dict]) -> None:
    """Cancella l'account (e tutti i suoi dati, art. 17 GDPR) a fine
    sessione/modulo — evita che i test lascino account accumulati (in
    locale contro un DB persistente come Atlas; il container MongoDB della
    CI è comunque effimero a ogni run)."""
    if not account:
        return
    try:
        requests.post(
            f"{API}/privacy/delete-account",
            json={"password": account["password"]},
            headers={"Authorization": f"Bearer {account['token']}"},
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        pass
