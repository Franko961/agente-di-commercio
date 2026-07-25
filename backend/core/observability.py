import asyncio
import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from core.database import db

# Timeout massimo per ogni scrittura di telemetria: se il DB è lento o
# irraggiungibile, la telemetria non deve mai far attendere a lungo
# l'operazione reale che sta osservando (una chiamata AI, un invio email,
# una richiesta HTTP) — meglio perdere un punto di dato che degradare
# l'esperienza utente.
_WRITE_TIMEOUT_SECONDS = 3.0

# ---------------------------------------------------------------------------
# Request ID: generato per ogni richiesta HTTP (o ripreso da un header
# X-Request-ID in ingresso, utile dietro un load balancer/proxy che già ne
# assegna uno), propagato nei log e nella risposta. Permette di correlare
# tutte le righe di log di una singola richiesta, e di far risalire
# rapidamente un utente che segnala un errore al log esatto lato server.
# ---------------------------------------------------------------------------
_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id_var.get()


def set_request_id(value: str) -> None:
    _request_id_var.set(value)


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


class JsonLogFormatter(logging.Formatter):
    """Formatter di logging che emette una riga JSON per ogni log, invece del
    testo libero attuale. Non richiede nessun servizio esterno: un log JSON
    è già "pronto" per essere spedito a qualunque aggregatore (Railway,
    Datadog, Grafana Loki, ecc.) il giorno in cui se ne collega uno, e nel
    frattempo resta comunque leggibile e grep-abile riga per riga."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Eventi di sistema: un log strutturato e persistito per le operazioni che
# oggi falliscono "in silenzio" dal punto di vista dell'app (visibili solo
# nei log testuali di Railway, non interrogabili) — chiamate AI, invio
# email, sincronizzazione Google Calendar. TTL a 30 giorni: serve per
# monitoraggio operativo recente, non come archivio permanente.
# ---------------------------------------------------------------------------
EVENT_TTL_SECONDS = 30 * 24 * 3600


async def record_event(category: str, status: str, **fields) -> None:
    """category: 'ai_call' | 'email_send' | 'calendar_sync' | ...
    status: 'success' | 'failure'
    fields: dettagli liberi (user_id, duration_ms, error, tokens_in, ecc.)

    Non solleva mai eccezioni: un problema nel registrare la telemetria non
    deve mai far fallire l'operazione reale che si sta osservando."""
    try:
        doc = {
            "category": category,
            "status": status,
            "created_at": datetime.now(timezone.utc),
            "request_id": get_request_id(),
            **fields,
        }
        await asyncio.wait_for(db.system_events.insert_one(doc), timeout=_WRITE_TIMEOUT_SECONDS)
    except Exception:
        logging.getLogger(__name__).exception("Impossibile registrare l'evento di sistema (non bloccante)")


# ---------------------------------------------------------------------------
# Metriche API a bucket per minuto: un documento per (metodo, percorso,
# minuto), aggiornato con $inc/$max — costo O(1) per richiesta, a differenza
# di un documento per singola richiesta che farebbe crescere la collection
# senza limite con il traffico. TTL a 7 giorni: è un cruscotto di salute
# recente, non uno storico da analisi a lungo termine (per quello servirebbe
# una pipeline dedicata, fuori scope qui).
# ---------------------------------------------------------------------------
API_METRICS_TTL_SECONDS = 7 * 24 * 3600


async def record_api_call(method: str, path_template: str, status_code: int, duration_ms: float) -> None:
    try:
        minute_bucket = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        key = f"{method}:{path_template}:{minute_bucket}"
        status_class = f"{status_code // 100}xx"
        await asyncio.wait_for(
            db.api_metrics_minute.update_one(
                {"_id": key},
                {
                    "$set": {
                        "method": method, "path": path_template,
                        "minute": minute_bucket, "created_at": datetime.now(timezone.utc),
                    },
                    "$inc": {
                        "count": 1,
                        "sum_duration_ms": duration_ms,
                        f"status_{status_class}": 1,
                    },
                    "$max": {"max_duration_ms": duration_ms},
                },
                upsert=True,
            ),
            timeout=_WRITE_TIMEOUT_SECONDS,
        )
    except Exception:
        logging.getLogger(__name__).exception("Impossibile registrare la metrica API (non bloccante)")


class Timer:
    """Piccolo helper per misurare una durata in millisecondi con `with`."""
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.duration_ms = (time.perf_counter() - self._start) * 1000
        return False
