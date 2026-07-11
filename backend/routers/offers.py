from fastapi import APIRouter, Depends, Body
from core.security import get_current_user
from services.offer_service import offer_service
from models.offer import OfferIn

router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.get("")
async def list_offers(user=Depends(get_current_user)):
    return await offer_service.list_offers(user)


@router.post("")
async def create_offer(payload: OfferIn, user=Depends(get_current_user)):
    return await offer_service.create_offer(user, payload)


@router.put("/{oid}")
async def update_offer(oid: str, payload: OfferIn, user=Depends(get_current_user)):
    await offer_service.update_offer(user, oid, payload)
    return {"ok": True}


@router.patch("/{oid}/status")
async def update_offer_status(oid: str, payload: dict = Body(...), user=Depends(get_current_user)):
    await offer_service.update_offer_status(user, oid, payload.get("status"))
    return {"ok": True}


@router.delete("/{oid}")
async def delete_offer(oid: str, user=Depends(get_current_user)):
    await offer_service.delete_offer(user, oid)
    return {"ok": True}
