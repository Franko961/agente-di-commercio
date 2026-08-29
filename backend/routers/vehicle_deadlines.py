from fastapi import APIRouter, Depends

from core.security import forbid_demo_write, get_current_user, require_module
from models.vehicle import VehicleDeadlineIn
from services.vehicle_deadline_service import vehicle_deadline_service

router = APIRouter(
    prefix="/api/vehicle-deadlines",
    tags=["vehicle-deadlines"],
    dependencies=[Depends(require_module("flotta"))],
)


@router.get("")
async def list_deadlines(user=Depends(get_current_user)):
    return await vehicle_deadline_service.list_deadlines(user)


@router.post("")
async def create_deadline(payload: VehicleDeadlineIn, user=Depends(forbid_demo_write)):
    return await vehicle_deadline_service.create_deadline(user, payload)


@router.put("/{did}")
async def update_deadline(
    did: str, payload: VehicleDeadlineIn, user=Depends(forbid_demo_write)
):
    await vehicle_deadline_service.update_deadline(user, did, payload)
    return {"ok": True}


@router.delete("/{did}")
async def delete_deadline(did: str, user=Depends(forbid_demo_write)):
    await vehicle_deadline_service.delete_deadline(user, did)
    return {"ok": True}
