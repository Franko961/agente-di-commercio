from fastapi import APIRouter, Depends, Body, Request
from core.security import get_current_user
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


@router.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    return await subscription_service.handle_stripe_webhook(request)


@router.post("/paypal-capture")
async def paypal_capture(payload: dict = Body(...), user=Depends(get_current_user)):
    return await subscription_service.paypal_capture(user, payload)


@router.post("/cancel")
async def cancel_subscription(user=Depends(get_current_user)):
    return await subscription_service.cancel_subscription(user)
