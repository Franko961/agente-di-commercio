"""
Test per core/observability.py: request id, formattatore di log JSON,
registrazione eventi di sistema (chiamate AI/email/calendar) e metriche API
a bucket per minuto. Nessun MongoDB reale: le collection sono sostituite con
fake in memoria.

Esegui con:
    JWT_SECRET=test MONGO_URL=mongodb://localhost DB_NAME=test \
    python -m pytest tests/test_observability.py -v
"""
import sys
import asyncio
import json
import logging

sys.path.insert(0, ".")

import core.observability as obs


def run(coro):
    return asyncio.run(coro)


class FakeUpdateResult:
    matched_count = 1


class FakeCollection:
    def __init__(self):
        self.inserted = []
        self.updates = []
        self.should_raise = False

    async def insert_one(self, doc):
        if self.should_raise:
            raise RuntimeError("DB down")
        self.inserted.append(doc)

    async def update_one(self, filter_, update, upsert=False):
        if self.should_raise:
            raise RuntimeError("DB down")
        self.updates.append({"filter": filter_, "update": update, "upsert": upsert})
        return FakeUpdateResult()


class FakeDb:
    def __init__(self):
        self.system_events = FakeCollection()
        self.api_metrics_minute = FakeCollection()


def test_request_id_default_e_set():
    assert obs.get_request_id() == "-"
    obs.set_request_id("abc123")
    assert obs.get_request_id() == "abc123"
    obs.set_request_id("-")  # reset per non sporcare altri test


def test_new_request_id_genera_valori_diversi():
    a = obs.new_request_id()
    b = obs.new_request_id()
    assert a != b
    assert len(a) == 16


def test_json_log_formatter_produce_json_valido():
    obs.set_request_id("req-1")
    formatter = obs.JsonLogFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="messaggio di prova", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["message"] == "messaggio di prova"
    assert parsed["level"] == "INFO"
    assert parsed["request_id"] == "req-1"
    assert "timestamp" in parsed
    obs.set_request_id("-")


def test_record_event_scrive_sulla_collection(monkeypatch):
    fake_db = FakeDb()
    monkeypatch.setattr(obs, "db", fake_db)

    run(obs.record_event("ai_call", "success", user_id="u1", tokens_in=100, tokens_out=50, cost_usd=0.002))

    assert len(fake_db.system_events.inserted) == 1
    doc = fake_db.system_events.inserted[0]
    assert doc["category"] == "ai_call"
    assert doc["status"] == "success"
    assert doc["user_id"] == "u1"
    assert doc["tokens_in"] == 100


def test_record_event_non_solleva_se_il_db_fallisce(monkeypatch):
    fake_db = FakeDb()
    fake_db.system_events.should_raise = True
    monkeypatch.setattr(obs, "db", fake_db)

    # Non deve sollevare: un problema nel registrare la telemetria non deve
    # mai far fallire l'operazione reale osservata.
    run(obs.record_event("email_send", "failure", error="timeout"))


def test_record_api_call_usa_upsert_con_inc_e_max(monkeypatch):
    fake_db = FakeDb()
    monkeypatch.setattr(obs, "db", fake_db)

    run(obs.record_api_call("GET", "/api/orders/{oid}", 200, 123.4))

    assert len(fake_db.api_metrics_minute.updates) == 1
    call = fake_db.api_metrics_minute.updates[0]
    assert call["upsert"] is True
    assert call["update"]["$inc"]["count"] == 1
    assert call["update"]["$inc"]["status_2xx"] == 1
    assert call["update"]["$max"]["max_duration_ms"] == 123.4


def test_record_api_call_classifica_5xx_correttamente(monkeypatch):
    fake_db = FakeDb()
    monkeypatch.setattr(obs, "db", fake_db)

    run(obs.record_api_call("POST", "/api/orders", 500, 50.0))

    call = fake_db.api_metrics_minute.updates[0]
    assert call["update"]["$inc"]["status_5xx"] == 1
    assert "status_2xx" not in call["update"]["$inc"]


def test_record_api_call_non_solleva_se_il_db_fallisce(monkeypatch):
    fake_db = FakeDb()
    fake_db.api_metrics_minute.should_raise = True
    monkeypatch.setattr(obs, "db", fake_db)

    run(obs.record_api_call("GET", "/api/clients", 200, 10.0))


def test_timer_misura_una_durata_positiva():
    with obs.Timer() as t:
        pass
    assert t.duration_ms >= 0
