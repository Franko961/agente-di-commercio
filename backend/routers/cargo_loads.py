from fastapi import APIRouter, Depends

from core.security import forbid_demo_write, get_current_user, require_module
from models.vehicle import CargoLoadIn, CargoLoadSign
from services.cargo_load_service import cargo_load_service

router = APIRouter(
    prefix="/api/cargo-loads",
    tags=["cargo-loads"],
    dependencies=[Depends(require_module("flotta"))],
)


@router.get("")
async def list_loads(user=Depends(get_current_user)):
    return await cargo_load_service.list_loads(user)


@router.post("")
async def create_load(payload: CargoLoadIn, user=Depends(forbid_demo_write)):
    return await cargo_load_service.create_load(user, payload)


@router.put("/{lid}")
async def update_load(lid: str, payload: CargoLoadIn, user=Depends(forbid_demo_write)):
    await cargo_load_service.update_load(user, lid, payload)
    return {"ok": True}


@router.post("/{lid}/sign")
async def sign_load(lid: str, payload: CargoLoadSign, user=Depends(forbid_demo_write)):
    await cargo_load_service.sign_load(
        user, lid, payload.signature, payload.signer_name
    )
    return {"ok": True}


@router.delete("/{lid}")
async def delete_load(lid: str, user=Depends(forbid_demo_write)):
    await cargo_load_service.delete_load(user, lid)
    return {"ok": True}
