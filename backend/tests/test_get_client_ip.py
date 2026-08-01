"""
Verifica get_client_ip() (core/security.py): l'IP usato come chiave per il
rate limiting (login, registrazione, richieste demo/contatti) dietro il
reverse proxy di Railway.

Il problema che risolve: request.client.host da solo è sempre l'IP del
proxy di Railway (identico per ogni visitatore), non quello reale — con
quello come chiave, un limite come "5 richieste demo all'ora" varrebbe per
TUTTI i visitatori messi insieme, bloccando il form per chiunque dopo le
prime 5 richieste globali. La correzione legge X-Forwarded-For, ma SOLO
l'N-esima voce da destra (N = TRUSTED_PROXY_HOPS, default 1): quella voce è
scritta da Railway stesso nell'atto di inoltrare la richiesta al
container, quindi non può essere falsificata da chi genera la richiesta —
a differenza della prima voce della lista, che un chiamante diretto può
impostare a piacere per aggirare il limite.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_get_client_ip.py -v
"""
import sys

sys.path.insert(0, ".")

import core.security as security_mod
from core.security import get_client_ip


class FakeClient:
    def __init__(self, host):
        self.host = host


class FakeRequest:
    def __init__(self, headers=None, client_host="10.0.0.5"):
        self.headers = headers or {}
        self.client = FakeClient(client_host) if client_host else None


def test_senza_x_forwarded_for_usa_request_client_host():
    """Nessun header (es. connessione diretta senza alcun proxy davanti):
    l'unico dato disponibile resta request.client.host."""
    request = FakeRequest(headers={}, client_host="203.0.113.9")
    assert get_client_ip(request) == "203.0.113.9"


def test_un_hop_fidato_prende_lunica_voce_presente(monkeypatch):
    """Configurazione di default (TRUSTED_PROXY_HOPS=1, solo Railway):
    con una sola voce in X-Forwarded-For (Railway ha aggiunto l'IP del
    visitatore che si è connesso direttamente a lui), quella è quanto di
    più affidabile si possa ottenere."""
    monkeypatch.setattr(security_mod, "TRUSTED_PROXY_HOPS", 1)
    request = FakeRequest(headers={"x-forwarded-for": "198.51.100.42"})
    assert get_client_ip(request) == "198.51.100.42"


def test_un_hop_fidato_ignora_le_voci_precedenti_alla_sua(monkeypatch):
    """Il caso centrale del fix: un chiamante malevolo può scrivere
    QUALUNQUE cosa nelle voci precedenti l'ultima (per aggirare il rate
    limit cambiando IP finto ad ogni richiesta) — solo l'ULTIMA voce,
    scritta da Railway stesso, va usata con TRUSTED_PROXY_HOPS=1."""
    monkeypatch.setattr(security_mod, "TRUSTED_PROXY_HOPS", 1)
    request = FakeRequest(headers={"x-forwarded-for": "1.2.3.4, 203.0.113.9"})
    assert get_client_ip(request) == "203.0.113.9"


def test_due_hop_fidati_prende_la_penultima_voce(monkeypatch):
    """Se in futuro si verifica che anche un secondo proxy (es. Netlify)
    aggiunge in modo affidabile il proprio hop, alzando TRUSTED_PROXY_HOPS
    a 2 si deve prendere la voce aggiunta da QUEL proxy (il vero IP del
    visitatore), non l'ultima (l'IP del secondo proxy stesso)."""
    monkeypatch.setattr(security_mod, "TRUSTED_PROXY_HOPS", 2)
    request = FakeRequest(headers={"x-forwarded-for": "203.0.113.9, 198.51.100.1"})
    assert get_client_ip(request) == "203.0.113.9"


def test_hop_fidati_maggiori_delle_voci_disponibili_ricade_su_client_host(monkeypatch):
    """TRUSTED_PROXY_HOPS configurato più alto di quante voci siano
    davvero presenti (es. un chiamante diretto senza passare da un secondo
    proxy, con TRUSTED_PROXY_HOPS=2): non bisogna inventarsi una voce che
    non esiste, meglio ricadere sul solo dato certo disponibile."""
    monkeypatch.setattr(security_mod, "TRUSTED_PROXY_HOPS", 2)
    request = FakeRequest(headers={"x-forwarded-for": "203.0.113.9"}, client_host="10.0.0.5")
    assert get_client_ip(request) == "10.0.0.5"


def test_header_vuoto_ricade_su_client_host(monkeypatch):
    monkeypatch.setattr(security_mod, "TRUSTED_PROXY_HOPS", 1)
    request = FakeRequest(headers={"x-forwarded-for": "   "}, client_host="10.0.0.5")
    assert get_client_ip(request) == "10.0.0.5"


def test_nessun_client_e_nessun_header_ritorna_none():
    request = FakeRequest(headers={}, client_host=None)
    assert get_client_ip(request) is None


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
