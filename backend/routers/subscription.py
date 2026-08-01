from fastapi import APIRouter, Depends, Body, Request
from core.security import get_current_user, get_client_ip
from services.subscription_service import subscription_service

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


@router.get("/plans")
async def get_plans():
    return await subscription_service.get_plans()


@router.get("/status")
async def subscription_status(user=Depends(get_current_user)):
    return await subscription_service.get_status(user)


@router.post("/create-stripe-session")
async def create_stripe_session(payload: dict = Body(...), user=Depends(get_current_user)):
    return await subscription_service.create_stripe_session(user, payload)


@router.post("/checkout-expired")
async def checkout_expired(payload: dict = Body(...), request: Request = None):
    """Endpoint pubblico: permette di avviare un pagamento Stripe a un utente il cui
    trial è scaduto e che quindi non può più autenticarsi. Richiede email+password
    nel body per verificare che sia il titolare dell'account (vedi payload atteso:
    email, password, plan, return_url)."""
    ip_address = get_client_ip(request) if request else None
    return await subscription_service.create_checkout_for_expired_account(payload, ip_address=ip_address)


@router.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    return await subscription_service.handle_stripe_webhook(request)


@router.post("/paypal-create")
async def paypal_create(payload: dict = Body(...), user=Depends(get_current_user)):
    return await subscription_service.create_paypal_subscription(user, payload)


@router.post("/paypal-capture")
async def paypal_capture(payload: dict = Body(...), user=Depends(get_current_user)):
    return await subscription_service.paypal_capture(user, payload)


@router.post("/paypal-webhook")
async def paypal_webhook(request: Request):
    return await subscription_service.handle_paypal_webhook(request)


@router.post("/cancel")
async def cancel_subscription(user=Depends(get_current_user)):
    return await subscription_service.cancel_subscription(user)
