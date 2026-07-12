from fastapi import APIRouter, Depends, Body
from core.security import get_current_user, forbid_demo_write
from services.commission_service import commission_service

router = APIRouter(prefix="/api/commissions", tags=["commissions"])


@router.get("")
async def list_commissions(user=Depends(get_current_user)):
    return await commission_service.list_commissions(user)


@router.get("/bonus-summary")
async def bonus_summary(user=Depends(get_current_user)):
    return await commission_service.bonus_summary(user)


@router.patch("/{cid}/status")
async def update_commission_status(cid: str, payload: dict = Body(...), user=Depends(get_current_user)):
    await commission_service.update_status(user, cid, payload.get("status"))
    return {"ok": True}


@router.delete("/{cid}")
async def delete_commission(cid: str, user=Depends(forbid_demo_write)):
    await commission_service.delete_commission(user, cid)
    return {"ok": True}
