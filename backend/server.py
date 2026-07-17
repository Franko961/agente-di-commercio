from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
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
from routers.orders import router as orders_router
from routers.expenses import router as expenses_router
from services.startup_service import run_startup, run_shutdown
from core.exceptions import AppError
from core.config import CORS_ORIGINS

app = FastAPI(title="Gestionale Agenti di Commercio")


@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
app.include_router(orders_router)
app.include_router(expenses_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
