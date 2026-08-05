from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write, require_module
from services.vehicle_cost_service import vehicle_cost_service
from models.vehicle import VehicleCostIn

router = APIRouter(prefix="/api/vehicle-costs", tags=["vehicle-costs"], dependencies=[Depends(require_module("flotta"))])


@router.get("")
async def list_costs(user=Depends(get_current_user)):
    return await vehicle_cost_service.list_costs(user)


@router.post("")
async def create_cost(payload: VehicleCostIn, user=Depends(forbid_demo_write)):
    return await vehicle_cost_service.create_cost(user, payload)


@router.put("/{cid}")
async def update_cost(cid: str, payload: VehicleCostIn, user=Depends(forbid_demo_write)):
    await vehicle_cost_service.update_cost(user, cid, payload)
    return {"ok": True}


@router.delete("/{cid}")
async def delete_cost(cid: str, user=Depends(forbid_demo_write)):
    await vehicle_cost_service.delete_cost(user, cid)
    return {"ok": True}
