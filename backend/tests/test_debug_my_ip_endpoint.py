"""
Verifica l'endpoint /api/debug/my-ip (protetto da require_admin): diagnostica
per confermare in produzione che get_client_ip() risolve davvero l'IP del
visitatore dietro il reverse proxy di Railway (e di Netlify per il traffico
via salesfly.it/api/*), non un IP fisso del proxy stesso — verifica manuale
descritta in core/config.py (TRUSTED_PROXY_HOPS). Non è più pubblico: pur
escludendo cookie/authorization dal dump, restava un endpoint che rivelava
dettagli dell'infrastruttura (header grezzi, trusted_proxy_hops) a chiunque
lo chiamasse, senza autenticazione.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_debug_my_ip_endpoint.py -v
"""

import asyncio

import server

FAKE_ADMIN = {"id": "admin-1", "email": "admin@test.it", "role": "admin"}


def run(coro):
    return asyncio.run(coro)


class FakeClient:
    def __init__(self, host):
        self.host = host


class FakeRequest:
    def __init__(self, headers=None, client_host="10.0.0.5"):
        self.headers = headers or {}
        self.client = FakeClient(client_host) if client_host else None


def all_routes(routes):
    """Starlette 1.x non appiattisce più le route incluse con
    include_router() dentro app.routes: ogni chiamata compare come un
    _IncludedRouter che va srotolato tramite original_router.routes per
    arrivare alle vere APIRoute/Route con un attributo .path."""
    flat = []
    for route in routes:
        if hasattr(route, "path"):
            flat.append(route)
        elif hasattr(route, "original_router"):
            flat.extend(all_routes(route.original_router.routes))
    return flat


def test_richiede_autenticazione_admin():
    routes = {r.path: r for r in all_routes(server.app.routes)}
    assert "/api/debug/my-ip" in routes
    deps = routes["/api/debug/my-ip"].dependant.dependencies
    assert len(deps) == 1
    assert deps[0].call is server.require_admin


def test_espone_ip_risolto_header_grezzo_e_peer_diretto():
    request = FakeRequest(
        headers={"x-forwarded-for": "203.0.113.9"}, client_host="10.0.0.5"
    )

    result = run(server.debug_my_ip(request, admin=FAKE_ADMIN))

    assert result["resolved_ip"] == "203.0.113.9"  # TRUSTED_PROXY_HOPS=1 di default
    assert result["x_forwarded_for"] == "203.0.113.9"
    assert result["direct_peer"] == "10.0.0.5"
    assert result["trusted_proxy_hops"] == 1


def test_senza_x_forwarded_for_ricade_sul_peer_diretto():
    request = FakeRequest(headers={}, client_host="10.0.0.5")

    result = run(server.debug_my_ip(request, admin=FAKE_ADMIN))

    assert result["resolved_ip"] == "10.0.0.5"
    assert result["x_forwarded_for"] is None


def test_nessun_campo_extra_oltre_ai_cinque_previsti():
    """Guardrail contro fughe di dati accidentali: solo i cinque campi
    diagnostici attesi, nient'altro (es. nessun dato di sessione/config)."""
    request = FakeRequest(headers={}, client_host="10.0.0.5")

    result = run(server.debug_my_ip(request, admin=FAKE_ADMIN))

    assert set(result.keys()) == {
        "resolved_ip",
        "x_forwarded_for",
        "direct_peer",
        "trusted_proxy_hops",
        "headers",
    }


def test_headers_esclude_cookie_e_authorization():
    """Anche se ora è protetto da require_admin, l'admin che chiama questo
    endpoint ha comunque una sessione attiva (è così che ha superato
    require_admin): il proprio token di sessione non deve mai finire
    riflesso indietro nella risposta JSON — difesa in profondità, non deve
    dipendere solo dal controllo di autenticazione a monte."""
    request = FakeRequest(
        headers={
            "cookie": "access_token=segreto-non-deve-uscire",
            "authorization": "Bearer segreto-anche-questo",
            "x-nf-client-connection-ip": "203.0.113.9",
        },
        client_host="10.0.0.5",
    )

    result = run(server.debug_my_ip(request, admin=FAKE_ADMIN))

    assert "cookie" not in result["headers"]
    assert "authorization" not in result["headers"]
    assert result["headers"]["x-nf-client-connection-ip"] == "203.0.113.9"
