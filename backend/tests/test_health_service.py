"""
Test per health_service.get_health(): la logica di aggregazione (tassi di
fallimento, ordinamento endpoint lenti/con errori) verificata con un fake
per db.*.aggregate() che restituisce righe pre-impostate — non re-implementa
la semantica reale di $group di MongoDB, ma verifica che i calcoli e
l'assemblaggio del risultato finale siano corretti.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_health_service.py -v
"""
import sys
import asyncio

sys.path.insert(0, ".")

import services.health_service as health_service_mod
from services.health_service import HealthService


def run(coro):
    return asyncio.run(coro)


class FakeAggregateCursor:
    def __init__(self, rows):
        self._rows = rows

    async def to_list(self, n):
        return self._rows[:n]


class FakeCollection:
    def __init__(self, rows_by_call):
        # rows_by_call: lista di liste, una per ogni chiamata ad aggregate(),
        # restituite in ordine di chiamata.
        self._rows_by_call = list(rows_by_call)
        self.calls = []

    def aggregate(self, pipeline):
        self.calls.append(pipeline)
        rows = self._rows_by_call.pop(0) if self._rows_by_call else []
        return FakeAggregateCursor(rows)


class FakeDb:
    def __init__(self, endpoints_rows, category_rows_sequence):
        self.api_metrics_minute = FakeCollection([endpoints_rows])
        # Una chiamata aggregate() per categoria (ai, email, calendar_sync),
        # nell'ordine in cui get_health le invoca.
        self.system_events = FakeCollection(category_rows_sequence)


def test_get_health_calcola_tasso_di_fallimento_ai(monkeypatch):
    fake_db = FakeDb(
        endpoints_rows=[],
        category_rows_sequence=[
            [{"_id": "success", "count": 8, "sum_cost_usd": 0.01, "sum_tokens_in": 800, "sum_tokens_out": 400},
             {"_id": "failure", "count": 2, "sum_cost_usd": 0.0, "sum_tokens_in": 0, "sum_tokens_out": 0}],
            [],  # email
            [],  # calendar_sync
        ],
    )
    monkeypatch.setattr(health_service_mod, "db", fake_db)
    service = HealthService()

    health = run(service.get_health(hours=24))

    assert health["ai"]["total"] == 10
    assert health["ai"]["success"] == 8
    assert health["ai"]["failure"] == 2
    assert health["ai"]["failure_rate_pct"] == 20.0
    assert health["ai"]["cost_usd"] == 0.01


def test_get_health_nessun_dato_non_rompe(monkeypatch):
    fake_db = FakeDb(endpoints_rows=[], category_rows_sequence=[[], [], []])
    monkeypatch.setattr(health_service_mod, "db", fake_db)
    service = HealthService()

    health = run(service.get_health(hours=24))

    assert health["ai"]["total"] == 0
    assert health["ai"]["failure_rate_pct"] == 0.0
    assert health["endpoints"]["slowest"] == []
    assert health["endpoints"]["most_errors"] == []


def test_get_health_ordina_endpoint_piu_lenti(monkeypatch):
    endpoints_rows = [
        {"method": "GET", "path": "/api/dashboard/stats", "count": 100,
         "avg_duration_ms": 850.0, "max_duration_ms": 1200.0, "status_4xx": 0, "status_5xx": 0, "error_rate_pct": 0.0},
        {"method": "GET", "path": "/api/clients", "count": 500,
         "avg_duration_ms": 45.0, "max_duration_ms": 200.0, "status_4xx": 0, "status_5xx": 0, "error_rate_pct": 0.0},
    ]
    fake_db = FakeDb(endpoints_rows=endpoints_rows, category_rows_sequence=[[], [], []])
    monkeypatch.setattr(health_service_mod, "db", fake_db)
    service = HealthService()

    health = run(service.get_health(hours=24))

    assert health["endpoints"]["slowest"][0]["path"] == "/api/dashboard/stats"
    assert health["endpoints"]["total_requests"] == 600


def test_get_health_filtra_solo_endpoint_con_errori(monkeypatch):
    endpoints_rows = [
        {"method": "GET", "path": "/api/ok", "count": 50,
         "avg_duration_ms": 20.0, "max_duration_ms": 40.0, "status_4xx": 0, "status_5xx": 0, "error_rate_pct": 0.0},
        {"method": "POST", "path": "/api/orders", "count": 20,
         "avg_duration_ms": 30.0, "max_duration_ms": 60.0, "status_4xx": 1, "status_5xx": 2, "error_rate_pct": 15.0},
    ]
    fake_db = FakeDb(endpoints_rows=endpoints_rows, category_rows_sequence=[[], [], []])
    monkeypatch.setattr(health_service_mod, "db", fake_db)
    service = HealthService()

    health = run(service.get_health(hours=24))

    assert len(health["endpoints"]["most_errors"]) == 1
    assert health["endpoints"]["most_errors"][0]["path"] == "/api/orders"
