from typing import Optional

from fastapi import APIRouter, Depends

from core.security import forbid_demo_write, get_current_user, require_module
from models.offer import OfferIn, OfferStatusIn, SignatureIn
from services.offer_service import offer_service

router = APIRouter(prefix="/api/offers", tags=["offers"])

# Solo le scritture legate al modulo "offerte": la lettura resta sempre
# disponibile perché Ordini.jsx mostra le offerte insieme agli ordini
# nella stessa pagina — bloccarla romperebbe quella pagina anche quando
# non è "Offerte" il modulo disattivato.
MODULE_DEP = Depends(require_module("offerte"))


@router.get("")
async def list_offers(
    mandante_id: Optional[str] = None, user=Depends(get_current_user)
):
    return await offer_service.list_offers(user, mandante_id)


@router.post("", dependencies=[MODULE_DEP])
async def create_offer(payload: OfferIn, user=Depends(forbid_demo_write)):
    return await offer_service.create_offer(user, payload)


@router.put("/{oid}", dependencies=[MODULE_DEP])
async def update_offer(oid: str, payload: OfferIn, user=Depends(forbid_demo_write)):
    await offer_service.update_offer(user, oid, payload)
    return {"ok": True}


@router.patch("/{oid}/status", dependencies=[MODULE_DEP])
async def update_offer_status(
    oid: str, payload: OfferStatusIn, user=Depends(forbid_demo_write)
):
    await offer_service.update_offer_status(user, oid, payload.status)
    return {"ok": True}


@router.delete("/{oid}", dependencies=[MODULE_DEP])
async def delete_offer(oid: str, user=Depends(forbid_demo_write)):
    await offer_service.delete_offer(user, oid)
    return {"ok": True}


@router.post("/{oid}/sign", dependencies=[MODULE_DEP])
async def sign_offer(oid: str, payload: SignatureIn, user=Depends(forbid_demo_write)):
    await offer_service.sign_offer(user, oid, payload.signature, payload.signer_name)
    return {"ok": True}
