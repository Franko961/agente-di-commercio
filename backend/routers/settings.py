from fastapi import APIRouter, Depends

from core.security import forbid_demo_write, get_current_user
from models.addresses import AddressesIn
from models.company_settings import CompanySettingsIn
from models.goals import GoalsIn
from models.leave_settings import LeaveSettingsIn
from services.attendance_service import attendance_service
from services.settings_service import settings_service

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
async def update_leave_settings(
    payload: LeaveSettingsIn, user=Depends(forbid_demo_write)
):
    return await settings_service.update_leave_settings(user, payload)


@router.get("/company")
async def get_company_settings(user=Depends(get_current_user)):
    return await settings_service.get_company_settings(user)


@router.put("/company")
async def update_company_settings(
    payload: CompanySettingsIn, user=Depends(forbid_demo_write)
):
    return await settings_service.update_company_settings(user, payload)


@router.get("/attendance-kiosk")
async def get_attendance_kiosk_status(user=Depends(get_current_user)):
    """Solo se un QR è già stato generato (bool), mai il token/hash —
    vedi attendance_service.get_kiosk_token_status."""
    return await attendance_service.get_kiosk_token_status(user)


@router.post("/attendance-kiosk/regenerate")
async def regenerate_attendance_kiosk_token(user=Depends(forbid_demo_write)):
    """Genera (o rigenera, invalidando il QR precedente) il token del
    chiosco di timbratura — restituito qui una sola volta perché il
    responsabile lo stampi/lo componga nel QR da affiggere all'ingresso."""
    token = await attendance_service.regenerate_kiosk_token(user)
    return {"token": token}
