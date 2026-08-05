from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import logging
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from routers.clients import router as clients_router
from routers.leads import router as leads_router
from routers.appointments import router as appointments_router
from routers.mandanti import router as mandanti_router
from routers.products import router as products_router
from routers.offers import router as offers_router
from routers.commissions import router as commissions_router
from routers.documents import router as documents_router
from routers.automations import router as automations_router
from routers.dashboard import router as dashboard_router
from routers.export import router as export_router
from routers.auth import router as auth_router
from routers.ai import router as ai_router
from routers.email import router as email_router
from routers.admin import router as admin_router
from routers.subscription import router as subscription_router
from routers.integrations import router as integrations_router
from routers.demo_requests import router as demo_requests_router
from routers.contact import router as contact_router
from routers.orders import router as orders_router
from routers.expenses import router as expenses_router
from routers.settings import router as settings_router
from routers.geocoding import router as geocoding_router
from routers.route_planning import router as route_planning_router
from routers.gdpr import router as gdpr_router
from routers.feedback import router as feedback_router
from routers.employees import router as employees_router
from routers.leave_requests import router as leave_requests_router
from routers.vehicles import router as vehicles_router
from routers.vehicle_deadlines import router as vehicle_deadlines_router
from routers.vehicle_costs import router as vehicle_costs_router
from routers.cargo_loads import router as cargo_loads_router
from services.startup_service import run_startup, run_shutdown
from core.exceptions import AppError
from core.config import CORS_ORIGINS, SENTRY_DSN, TRUSTED_PROXY_HOPS
from core.observability import configure_logging, new_request_id, set_request_id, record_api_call, init_opentelemetry
from core.security import get_client_ip

app = FastAPI(title="Gestionale Agenti di Commercio")


@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


configure_logging()

# Sentry si attiva solo se SENTRY_DSN è configurato: senza quella variabile
# d'ambiente questo blocco non fa nulla, non serve un account per il resto
# della telemetria (request id, metriche API, eventi di sistema) che
# funziona comunque. Il giorno in cui si crea un account Sentry (anche
# gratuito) e si imposta SENTRY_DSN, il tracciamento errori con stack trace
# si attiva senza altre modifiche al codice.
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        sentry_sdk.init(dsn=SENTRY_DSN, integrations=[FastApiIntegration()], traces_sample_rate=0.1)
        logging.getLogger(__name__).info("Sentry inizializzato")
    except Exception as e:
        logging.getLogger(__name__).error(f"Inizializzazione Sentry fallita: {e}")

# OpenTelemetry: stesso principio, spento finché non si imposta
# OTEL_EXPORTER_OTLP_ENDPOINT (vedi core/observability.init_opentelemetry).
try:
    if init_opentelemetry(app):
        logging.getLogger(__name__).info("OpenTelemetry inizializzato")
except Exception as e:
    logging.getLogger(__name__).error(f"Inizializzazione OpenTelemetry fallita: {e}")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Assegna un request id ad ogni richiesta (ripreso da X-Request-ID se
    già presente, es. da un proxy a monte) e ne misura la durata, salvando
    un'aggregazione per minuto/endpoint in api_metrics_minute — la base per
    rispondere a "quale endpoint è lento" senza un servizio esterno."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("x-request-id") or new_request_id()
        set_request_id(req_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            path_template = _route_path(request)
            await record_api_call(request.method, path_template, 500, duration_ms)
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        path_template = _route_path(request)
        await record_api_call(request.method, path_template, response.status_code, duration_ms)
        response.headers["X-Request-ID"] = req_id
        return response


def _route_path(request: Request) -> str:
    """Percorso 'a template' (es. /api/orders/{oid}) invece del percorso
    letterale con l'id reale sostituito dentro — altrimenti ogni ordine/
    cliente/documento diverso creerebbe un bucket di metriche a parte,
    invece di aggregare tutte le chiamate allo stesso endpoint insieme."""
    route = request.scope.get("route")
    return route.path if route else request.url.path


# Pubblico e senza autenticazione apposta: usato da Railway, reverse proxy,
# uptime monitor e sistemi di riavvio automatico per sapere se il processo è
# vivo, prima ancora che un utente faccia login — /api/admin/health (sopra,
# nel router admin) resta il cruscotto con i dettagli tecnici, protetto da
# require_admin. Risposta minimale apposta: nessun dato su database,
# metriche o configurazione deve trapelare da un endpoint non autenticato.
@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Diagnostica pubblica per verificare in produzione cosa vede DAVVERO il
# server dietro il reverse proxy di Railway (e di Netlify per il traffico
# via salesfly.it/api/*): apri questo URL da due reti diverse (es. wifi di
# casa e dati mobili) e confronta resolved_ip — deve essere DIVERSO tra le
# due, e coincidere con l'IP reale del dispositivo usato, non con un IP
# fisso di Railway. Se resolved_ip risultasse identico da reti diverse,
# TRUSTED_PROXY_HOPS (core/config.py) andrebbe rivisto. Nessun dato
# sensibile esposto: solo l'IP/gli header della richiesta stessa, stesso
# principio di un servizio pubblico "whatismyip" — chi chiama vede solo
# informazioni sulla propria connessione.
@app.get("/api/debug/my-ip")
async def debug_my_ip(request: Request):
    return {
        "resolved_ip": get_client_ip(request),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "direct_peer": request.client.host if request.client else None,
        "trusted_proxy_hops": TRUSTED_PROXY_HOPS,
    }


@app.on_event("startup")
async def startup():
    await run_startup()


@app.on_event("shutdown")
async def shutdown():
    await run_shutdown()


# ----------------- App wiring -----------------
app.include_router(clients_router)
app.include_router(leads_router)
app.include_router(appointments_router)
app.include_router(mandanti_router)
app.include_router(products_router)
app.include_router(offers_router)
app.include_router(commissions_router)
app.include_router(documents_router)
app.include_router(automations_router)
app.include_router(dashboard_router)
app.include_router(export_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(email_router)
app.include_router(admin_router)
app.include_router(subscription_router)
app.include_router(integrations_router)
app.include_router(demo_requests_router)
app.include_router(contact_router)
app.include_router(orders_router)
app.include_router(expenses_router)
app.include_router(settings_router)
app.include_router(geocoding_router)
app.include_router(route_planning_router)
app.include_router(gdpr_router)
app.include_router(feedback_router)
app.include_router(employees_router)
app.include_router(leave_requests_router)
app.include_router(vehicles_router)
app.include_router(vehicle_deadlines_router)
app.include_router(vehicle_costs_router)
app.include_router(cargo_loads_router)

app.add_middleware(ObservabilityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
