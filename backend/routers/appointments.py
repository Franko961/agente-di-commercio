from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write
from services.appointment_service import appointment_service
from models.appointment import AppointmentIn

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

@router.get("")
async def list_appointments(user=Depends(get_current_user)):
    return await appointment_service.list_appointments(user)

@router.post("")
async def create_appointment(payload: AppointmentIn, user=Depends(get_current_user)):
    return await appointment_service.create_appointment(user, payload)

@router.put("/{aid}")
async def update_appointment(aid: str, payload: AppointmentIn, user=Depends(get_current_user)):
    await appointment_service.update_appointment(user, aid, payload)
    return {"ok": True}

@router.delete("/{aid}")
async def delete_appointment(aid: str, user=Depends(forbid_demo_write)):
    await appointment_service.delete_appointment(user, aid)
    return {"ok": True}
