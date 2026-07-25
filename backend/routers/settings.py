from fastapi import APIRouter, Depends
from core.security import get_current_user
from services.settings_service import settings_service
from models.goals import GoalsIn

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/goals")
async def get_goals(user=Depends(get_current_user)):
    return await settings_service.get_goals(user)


@router.put("/goals")
async def update_goals(payload: GoalsIn, user=Depends(get_current_user)):
    return await settings_service.update_goals(user, payload)
