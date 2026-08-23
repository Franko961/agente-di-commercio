"""
Verifica l'endpoint pubblico /api/debug/my-ip: diagnostica per confermare
in produzione che get_client_ip() risolve davvero l'IP del visitatore
dietro il reverse proxy di Railway (e di Netlify per il traffico via
salesfly.it/api/*), non un IP fisso del proxy stesso — verifica manuale
descritta in core/config.py (TRUSTED_PROXY_HOPS). Nessun dato sensibile:
solo l'IP/gli header della richiesta stessa, letti dal chiamante su di sé.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_debug_my_ip_endpoint.py -v
"""
import asyncio

import server


def run(coro):
    return asyncio.run(coro)


class FakeClient:
    def __init__(self, host):
        self.host = host


class FakeRequest:
    def __init__(self, headers=None, client_host="10.0.0.5"):
        self.headers = headers or {}
        self.client = FakeClient(client_host) if client_host else None


def test_registrato_pubblicamente_senza_autenticazione():
    routes = {r.path: r for r in server.app.routes}
    assert "/api/debug/my-ip" in routes
    assert routes["/api/debug/my-ip"].dependant.dependencies == []


def test_espone_ip_risolto_header_grezzo_e_peer_diretto():
    request = FakeRequest(headers={"x-forwarded-for": "203.0.113.9"}, client_host="10.0.0.5")

    result = run(server.debug_my_ip(request))

    assert result["resolved_ip"] == "203.0.113.9"  # TRUSTED_PROXY_HOPS=1 di default
    assert result["x_forwarded_for"] == "203.0.113.9"
    assert result["direct_peer"] == "10.0.0.5"
    assert result["trusted_proxy_hops"] == 1


def test_senza_x_forwarded_for_ricade_sul_peer_diretto():
    request = FakeRequest(headers={}, client_host="10.0.0.5")

    result = run(server.debug_my_ip(request))

    assert result["resolved_ip"] == "10.0.0.5"
    assert result["x_forwarded_for"] is None


def test_nessun_campo_extra_oltre_ai_cinque_previsti():
    """Guardrail contro fughe di dati accidentali: solo i cinque campi
    diagnostici attesi, nient'altro (es. nessun dato di sessione/config)."""
    request = FakeRequest(headers={}, client_host="10.0.0.5")

    result = run(server.debug_my_ip(request))

    assert set(result.keys()) == {"resolved_ip", "x_forwarded_for", "direct_peer", "trusted_proxy_hops", "headers"}


def test_headers_esclude_cookie_e_authorization():
    """Chi chiama questo endpoint pubblico potrebbe avere una sessione attiva
    (es. testato dal browser già loggato): il proprio token di sessione non
    deve mai finire riflesso indietro nella risposta JSON."""
    request = FakeRequest(headers={
        "cookie": "access_token=segreto-non-deve-uscire",
        "authorization": "Bearer segreto-anche-questo",
        "x-nf-client-connection-ip": "203.0.113.9",
    }, client_host="10.0.0.5")

    result = run(server.debug_my_ip(request))

    assert "cookie" not in result["headers"]
    assert "authorization" not in result["headers"]
    assert result["headers"]["x-nf-client-connection-ip"] == "203.0.113.9"
