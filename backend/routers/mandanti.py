from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write
from services.mandante_service import mandante_service
from models.mandante import MandanteIn

router = APIRouter(prefix="/api/mandanti", tags=["mandanti"])


@router.get("")
async def list_mandanti(user=Depends(get_current_user)):
    return await mandante_service.list_mandanti(user)


@router.post("")
async def create_mandante(payload: MandanteIn, user=Depends(get_current_user)):
    return await mandante_service.create_mandante(user, payload)


@router.put("/{mid}")
async def update_mandante(mid: str, payload: MandanteIn, user=Depends(get_current_user)):
    await mandante_service.update_mandante(user, mid, payload)
    return {"ok": True}


@router.delete("/{mid}")
async def delete_mandante(mid: str, user=Depends(forbid_demo_write)):
    await mandante_service.delete_mandante(user, mid)
    return {"ok": True}

