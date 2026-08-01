from fastapi import APIRouter, Depends, Body
from typing import Optional
from core.security import get_current_user, forbid_demo_write
from services.commission_service import commission_service
from models.commission import ManualCommissionIn

router = APIRouter(prefix="/api/commissions", tags=["commissions"])


@router.get("")
async def list_commissions(mandante_id: Optional[str] = None, user=Depends(get_current_user)):
    return await commission_service.list_commissions(user, mandante_id)


@router.get("/bonus-summary")
async def bonus_summary(user=Depends(get_current_user)):
    return await commission_service.bonus_summary(user)


# Percorsi letterali ("/manual", "/manual/{period}") dichiarati PRIMA di
# "/{cid}/status" e "/{cid}" più sotto: non collidono per forma (numero di
# segmenti diverso), ma stare comunque prima segue la stessa convenzione
# già adottata nel resto del router (percorsi specifici prima di quelli
# parametrizzati).
@router.get("/manual")
async def list_manual_commissions(user=Depends(get_current_user)):
    return await commission_service.list_manual_commissions(user)


@router.put("/manual")
async def set_manual_commission(payload: ManualCommissionIn, user=Depends(forbid_demo_write)):
    return await commission_service.set_manual_commission(user, payload.period, payload.amount)


@router.delete("/manual/{period}")
async def delete_manual_commission(period: str, user=Depends(forbid_demo_write)):
    await commission_service.delete_manual_commission(user, period)
    return {"ok": True}


@router.patch("/{cid}/status")
async def update_commission_status(cid: str, payload: dict = Body(...), user=Depends(forbid_demo_write)):
    await commission_service.update_status(user, cid, payload.get("status"))
    return {"ok": True}


@router.delete("/{cid}")
async def delete_commission(cid: str, user=Depends(forbid_demo_write)):
    await commission_service.delete_commission(user, cid)
    return {"ok": True}
