from fastapi import APIRouter, Depends, Body
from core.security import get_current_user
from services.lead_service import lead_service
from models.lead import LeadIn

router = APIRouter(prefix="/api/leads", tags=["leads"])

@router.get("")
async def list_leads(user=Depends(get_current_user)):
    return await lead_service.list_leads(user)

@router.post("")
async def create_lead(payload: LeadIn, user=Depends(get_current_user)):
    return await lead_service.create_lead(user, payload)

@router.put("/{lid}")
async def update_lead(lid: str, payload: LeadIn, user=Depends(get_current_user)):
    await lead_service.update_lead(user, lid, payload)
    return {"ok": True}

@router.patch("/{lid}/status")
async def update_lead_status(lid: str, payload: dict = Body(...), user=Depends(get_current_user)):
    await lead_service.update_status(user, lid, payload.get("status"))
    return {"ok": True}

@router.delete("/{lid}")
async def delete_lead(lid: str, user=Depends(get_current_user)):
    await lead_service.delete_lead(user, lid)
    return {"ok": True}
