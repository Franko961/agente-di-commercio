"""Smoke test contro l'ambiente di PRODUZIONE reale (https://salesfly.it),
non contro un backend locale/CI.

I test in backend/tests/ girano contro un backend "nudo" avviato in CI
(solo uvicorn, nessun proxy davanti) — non possono mai verificare che
manifest.json/sw.js siano serviti sulla stessa origin del frontend, perché
quel comportamento dipende dal proxy Netlify→Railway
(frontend/public/_redirects), che esiste solo su salesfly.it reale.
Questo file colma quella lacuna, come categoria di test separata: gira solo
da .github/workflows/smoke-test.yml (push su main + schedulato + manuale),
MAI dalla pipeline di CI/PR (backend/tests/ resta hermetic, offline,
riproducibile — vedi .github/workflows/ci.yml).
"""

import time

import requests

BASE_URL = "https://salesfly.it"
API = f"{BASE_URL}/api"


def _wait_for_health(timeout_seconds: int = 300, interval_seconds: int = 15) -> None:
    """Attende che il backend risponda, per tollerare il tempo di
    propagazione del deploy Railway/Netlify dopo un push su main — le run
    schedulate/manuali passano al primo tentativo, non serve un'attesa
    reale per quelle."""
    deadline = time.monotonic() + timeout_seconds
    last_error = "nessun tentativo effettuato"
    while time.monotonic() < deadline:
        try:
            r = requests.get(f"{API}/health", timeout=10)
            if r.status_code == 200:
                return
            last_error = f"status {r.status_code}: {r.text[:200]}"
        except requests.exceptions.RequestException as e:
            last_error = str(e)
        time.sleep(interval_seconds)
    raise AssertionError(
        f"Backend non raggiungibile dopo {timeout_seconds}s: {last_error}"
    )


# Definito per primo apposta: pytest esegue i test in ordine di definizione
# (non alfabetico) all'interno di un modulo — questo deve girare prima
# degli altri, così un deploy ancora in corso produce un errore chiaro
# ("backend non raggiungibile") invece di far fallire ogni test in modo
# scollegato.
def test_health_reachable():
    _wait_for_health()


def test_manifest_served_same_origin():
    r = requests.get(f"{BASE_URL}/manifest.json", timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert d["theme_color"] == "#0A192F"
    assert "agenti" in d["description"].lower()


def test_service_worker_served_same_origin():
    r = requests.get(f"{BASE_URL}/sw.js", timeout=20)
    assert r.status_code == 200
    assert "CACHE_VERSION" in r.text or "caches.open" in r.text


def test_login_rejects_wrong_credentials_via_proxy():
    """Verifica che l'intera catena di autenticazione funzioni davvero in
    produzione (proxy Netlify→Railway incluso, backend, DB, JWT) — senza
    dipendere da un account reale: in produzione non esiste un account
    demo pubblico (nessun codice imposta mai is_demo=True su un nuovo
    account, verificato nel repo), quindi non c'è nessuna credenziale
    valida "sicura" da usare qui. Una password sbagliata deve comunque
    ricevere 401 dalla catena intera, non un errore di rete/proxy/5xx —
    prova che l'endpoint è vivo e funzionante end-to-end senza scrivere
    né esporre nulla."""
    r = requests.post(
        f"{API}/auth/login",
        json={"email": "smoke-test@salesfly.it", "password": "wrong-password"},
        timeout=20,
    )
    assert r.status_code == 401, r.text
