from fastapi import APIRouter, Depends
from core.security import get_current_user
from services.dashboard_service import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def dashboard(user=Depends(get_current_user)):
    return await dashboard_service.get_stats(user)


@router.get("/today")
async def dashboard_today(user=Depends(get_current_user)):
    return await dashboard_service.get_today_brief(user)
