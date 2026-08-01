from fastapi import APIRouter, Depends
from typing import Optional
from core.security import get_current_user, forbid_demo_write
from services.offer_service import offer_service
from models.offer import OfferIn, OfferStatusIn, SignatureIn

router = APIRouter(prefix="/api/offers", tags=["offers"])


@router.get("")
async def list_offers(mandante_id: Optional[str] = None, user=Depends(get_current_user)):
    return await offer_service.list_offers(user, mandante_id)


@router.post("")
async def create_offer(payload: OfferIn, user=Depends(forbid_demo_write)):
    return await offer_service.create_offer(user, payload)


@router.put("/{oid}")
async def update_offer(oid: str, payload: OfferIn, user=Depends(forbid_demo_write)):
    await offer_service.update_offer(user, oid, payload)
    return {"ok": True}


@router.patch("/{oid}/status")
async def update_offer_status(oid: str, payload: OfferStatusIn, user=Depends(forbid_demo_write)):
    await offer_service.update_offer_status(user, oid, payload.status)
    return {"ok": True}


@router.delete("/{oid}")
async def delete_offer(oid: str, user=Depends(forbid_demo_write)):
    await offer_service.delete_offer(user, oid)
    return {"ok": True}


@router.post("/{oid}/sign")
async def sign_offer(oid: str, payload: SignatureIn, user=Depends(forbid_demo_write)):
    await offer_service.sign_offer(user, oid, payload.signature, payload.signer_name)
    return {"ok": True}
