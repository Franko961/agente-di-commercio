from fastapi import APIRouter, Depends

from core.security import forbid_demo_write, get_current_user, require_module
from models.vehicle import VehicleActiveUpdate, VehicleIn
from services.vehicle_service import vehicle_service

# Modulo interamente autenticato (nessun endpoint pubblico come in
# leave_requests.py): può essere gated a livello di intero router, senza
# bisogno del pattern per-endpoint usato per i moduli core con dati di
# riferimento condivisi tra pagine (clienti, mandanti, prodotti, offerte).
router = APIRouter(
    prefix="/api/vehicles",
    tags=["vehicles"],
    dependencies=[Depends(require_module("flotta"))],
)


@router.get("")
async def list_vehicles(user=Depends(get_current_user)):
    return await vehicle_service.list_vehicles(user)


@router.post("")
async def create_vehicle(payload: VehicleIn, user=Depends(forbid_demo_write)):
    return await vehicle_service.create_vehicle(user, payload)


@router.put("/{vid}")
async def update_vehicle(vid: str, payload: VehicleIn, user=Depends(forbid_demo_write)):
    await vehicle_service.update_vehicle(user, vid, payload)
    return {"ok": True}


@router.patch("/{vid}/active")
async def set_vehicle_active(
    vid: str, payload: VehicleActiveUpdate, user=Depends(forbid_demo_write)
):
    await vehicle_service.set_active(user, vid, payload.active)
    return {"ok": True}


@router.delete("/{vid}")
async def delete_vehicle(vid: str, user=Depends(forbid_demo_write)):
    await vehicle_service.delete_vehicle(user, vid)
    return {"ok": True}
