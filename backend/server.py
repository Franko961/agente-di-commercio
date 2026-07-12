from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import logging
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Body
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from core.database import db
from core.security import get_current_user
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
from services.startup_service import run_startup, run_shutdown

# ----------------- Setup -----------------

from core.config import PLANS

# Stripe & PayPal
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')  # 'sandbox' o 'live'


app = FastAPI(title="Gestionale Agenti di Commercio")
api = APIRouter(prefix="/api")

from core.exceptions import AppError

@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ----------------- Subscription & Payments -----------------

def subscription_active(user: dict) -> bool:
    status = user.get("subscription_status", "trial")
    if status == "active":
        return True
    if status == "trial":
        trial_end = user.get("trial_ends_at", "")
        try:
            from datetime import datetime, timezone
            end = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) < end
        except Exception:
            return True
    return False


@api.get("/subscription/plans")
async def get_plans():
    return [{"id": k, **v} for k, v in PLANS.items()]


@api.get("/subscription/status")
async def subscription_status(user=Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return {
        "plan": u.get("plan", "base"),
        "status": u.get("subscription_status", "trial"),
        "trial_ends_at": u.get("trial_ends_at"),
        "active": subscription_active(u),
    }


@api.post("/subscription/create-stripe-session")
async def create_stripe_session(payload: dict = Body(...), user=Depends(get_current_user)):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(500, "Stripe non configurato")
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        plan_id = payload.get("plan", "base")
        plan = PLANS.get(plan_id)
        if not plan:
            raise HTTPException(400, "Piano non valido")

        # Crea o recupera customer Stripe
        u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
        customer_id = u.get("stripe_customer_id")
        if not customer_id:
            customer = stripe.Customer.create(email=user["email"], name=u.get("name", ""))
            customer_id = customer.id
            await db.users.update_one({"id": user["id"]}, {"$set": {"stripe_customer_id": customer_id}})

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": plan["stripe_price_id"], "quantity": 1}],
            success_url=f"{payload.get('return_url', 'https://salesfly.netlify.app')}/abbonamento?success=stripe",
            cancel_url=f"{payload.get('return_url', 'https://salesfly.netlify.app')}/abbonamento?cancelled=1",
            metadata={"user_id": user["id"], "plan": plan_id},
        )
        return {"url": session.url}
    except Exception as e:
        logger.error(f"Stripe session error: {e}")
        raise HTTPException(500, str(e)[:200])


@api.post("/subscription/stripe-webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(500, "Stripe non configurato")
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(400, str(e))

    if event["type"] == "checkout.session.completed":
        meta = event["data"]["object"].get("metadata", {})
        user_id = meta.get("user_id")
        plan = meta.get("plan", "base")
        sub_id = event["data"]["object"].get("subscription")
        if user_id:
            await db.users.update_one({"id": user_id}, {"$set": {
                "plan": plan,
                "subscription_status": "active",
                "stripe_subscription_id": sub_id,
            }})
    elif event["type"] in ("customer.subscription.deleted", "customer.subscription.paused"):
        sub = event["data"]["object"]
        await db.users.update_one(
            {"stripe_subscription_id": sub["id"]},
            {"$set": {"subscription_status": "cancelled"}}
        )
    return {"ok": True}


@api.post("/subscription/paypal-capture")
async def paypal_capture(payload: dict = Body(...), user=Depends(get_current_user)):
    """Conferma abbonamento PayPal dopo approvazione."""
    subscription_id = payload.get("subscription_id")
    plan_id = payload.get("plan", "base")
    if not subscription_id:
        raise HTTPException(400, "subscription_id mancante")
    await db.users.update_one({"id": user["id"]}, {"$set": {
        "plan": plan_id,
        "subscription_status": "active",
        "paypal_subscription_id": subscription_id,
    }})
    return {"ok": True}


@api.post("/subscription/cancel")
async def cancel_subscription(user=Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    # Cancella su Stripe se presente
    if u.get("stripe_subscription_id") and STRIPE_SECRET_KEY:
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            stripe.Subscription.cancel(u["stripe_subscription_id"])
        except Exception as e:
            logger.warning(f"Stripe cancel error: {e}")
    await db.users.update_one({"id": user["id"]}, {"$set": {"subscription_status": "cancelled"}})
    return {"ok": True}


# ----------------- Startup / Shutdown -----------------
@app.on_event("startup")
async def startup():
    await run_startup()


@app.on_event("shutdown")
async def shutdown():
    await run_shutdown()


# ----------------- App wiring -----------------
app.include_router(api)
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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["https://salesfly.it", "https://www.salesfly.it", "https://main--salesfly.netlify.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)
