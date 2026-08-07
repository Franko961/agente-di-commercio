from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write
from services.settings_service import settings_service
from models.goals import GoalsIn
from models.addresses import AddressesIn
from models.leave_settings import LeaveSettingsIn

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/goals")
async def get_goals(user=Depends(get_current_user)):
    return await settings_service.get_goals(user)


@router.put("/goals")
async def update_goals(payload: GoalsIn, user=Depends(forbid_demo_write)):
    return await settings_service.update_goals(user, payload)


@router.get("/addresses")
async def get_addresses(user=Depends(get_current_user)):
    return await settings_service.get_addresses(user)


@router.put("/addresses")
async def update_addresses(payload: AddressesIn, user=Depends(forbid_demo_write)):
    return await settings_service.update_addresses(user, payload)


@router.get("/leave")
async def get_leave_settings(user=Depends(get_current_user)):
    return await settings_service.get_leave_settings(user)


@router.put("/leave")
async def update_leave_settings(payload: LeaveSettingsIn, user=Depends(forbid_demo_write)):
    return await settings_service.update_leave_settings(user, payload)
