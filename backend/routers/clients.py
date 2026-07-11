from fastapi import APIRouter, Depends
from typing import Optional
from core.security import get_current_user
from services.client_service import client_service
from models.client import ClientIn

router = APIRouter(prefix="/api/clients", tags=["clients"])

@router.get("")
async def list_clients(zone: Optional[str] = None, sector: Optional[str] = None,
                        potential: Optional[str] = None, q: Optional[str] = None,
                        user=Depends(get_current_user)):
    return await client_service.list_clients(user, zone, sector, potential, q)

@router.post("")
async def create_client(payload: ClientIn, user=Depends(get_current_user)):
    return await client_service.create_client(user, payload)

@router.get("/{cid}")
async def get_client(cid: str, user=Depends(get_current_user)):
    return await client_service.get_client(user, cid)

@router.put("/{cid}")
async def update_client(cid: str, payload: ClientIn, user=Depends(get_current_user)):
    await client_service.update_client(user, cid, payload)
    return {"ok": True}

@router.delete("/{cid}")
async def delete_client(cid: str, user=Depends(get_current_user)):
    await client_service.delete_client(user, cid)
    return {"ok": True}
