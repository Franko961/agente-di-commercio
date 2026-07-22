from fastapi import APIRouter, Depends
from typing import Optional
from core.security import get_current_user
from services.dashboard_service import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def dashboard(mandante_id: Optional[str] = None, user=Depends(get_current_user)):
    return await dashboard_service.get_stats(user, mandante_id)


@router.get("/today")
async def dashboard_today(mandante_id: Optional[str] = None, user=Depends(get_current_user)):
    return await dashboard_service.get_today_brief(user, mandante_id)
