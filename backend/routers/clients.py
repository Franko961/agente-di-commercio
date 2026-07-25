from fastapi import APIRouter, Depends
from typing import Optional
from core.security import get_current_user, forbid_demo_write
from services.client_service import client_service
from models.client import ClientIn, ClientBulkIn

router = APIRouter(prefix="/api/clients", tags=["clients"])

@router.get("")
async def list_clients(zone: Optional[str] = None, sector: Optional[str] = None,
                        potential: Optional[str] = None, q: Optional[str] = None,
                        mandante_id: Optional[str] = None,
                        user=Depends(get_current_user)):
    return await client_service.list_clients(user, zone, sector, potential, q, mandante_id)

@router.post("")
async def create_client(payload: ClientIn, user=Depends(get_current_user)):
    return await client_service.create_client(user, payload)

@router.post("/bulk")
async def bulk_import_clients(payload: ClientBulkIn, user=Depends(forbid_demo_write)):
    """Importa in blocco clienti da un file CSV/Excel caricato dall'utente
    (parsing già fatto lato frontend). Deduplica per partita IVA, o per
    ragione sociale + città quando la P.IVA non è indicata."""
    return await client_service.bulk_import(user, payload)

@router.get("/{cid}")
async def get_client(cid: str, user=Depends(get_current_user)):
    return await client_service.get_client(user, cid)

@router.put("/{cid}")
async def update_client(cid: str, payload: ClientIn, user=Depends(get_current_user)):
    await client_service.update_client(user, cid, payload)
    return {"ok": True}

@router.delete("/{cid}")
async def delete_client(cid: str, user=Depends(forbid_demo_write)):
    await client_service.delete_client(user, cid)
    return {"ok": True}
