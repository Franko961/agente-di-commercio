"""
Verifica l'endpoint pubblico di health check (/health e /api/health, non
autenticato) usato da Railway, reverse proxy e uptime monitor per sapere se
il processo è vivo — distinto da /api/admin/health (protetto da
require_admin), che espone invece un cruscotto tecnico dettagliato.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_public_health_endpoint.py -v
"""

import asyncio

import server


def run(coro):
    return asyncio.run(coro)


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


def test_risposta_minimale_senza_dati_tecnici():
    result = run(server.health())

    assert result == {"status": "ok"}


def test_registrato_su_entrambi_i_percorsi_pubblici():
    paths = {route.path for route in all_routes(server.app.routes)}

    assert "/health" in paths
    assert "/api/health" in paths


def test_nessuna_autenticazione_richiesta():
    for route in all_routes(server.app.routes):
        if route.path in ("/health", "/api/health"):
            assert route.dependant.dependencies == []
