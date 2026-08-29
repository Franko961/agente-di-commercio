from fastapi import APIRouter, Depends

from core.security import forbid_demo_write, get_current_user, require_module
from models.lead import LeadContactIn, LeadIn, LeadStatusIn
from services.lead_service import lead_service

router = APIRouter(
    prefix="/api/leads", tags=["leads"], dependencies=[Depends(require_module("lead"))]
)


@router.get("")
async def list_leads(user=Depends(get_current_user)):
    return await lead_service.list_leads(user)


@router.post("")
async def create_lead(payload: LeadIn, user=Depends(forbid_demo_write)):
    return await lead_service.create_lead(user, payload)


@router.put("/{lid}")
async def update_lead(lid: str, payload: LeadIn, user=Depends(forbid_demo_write)):
    await lead_service.update_lead(user, lid, payload)
    return {"ok": True}


@router.patch("/{lid}/status")
async def update_lead_status(
    lid: str, payload: LeadStatusIn, user=Depends(forbid_demo_write)
):
    await lead_service.update_status(user, lid, payload.status)
    return {"ok": True}


@router.post("/{lid}/log-contact")
async def log_contact(
    lid: str, payload: LeadContactIn, user=Depends(forbid_demo_write)
):
    """Registra esplicitamente un contatto avvenuto col lead (chiamata,
    email, incontro), aggiornando last_contact_at/last_interaction_at senza
    dover passare da una modifica completa del lead."""
    await lead_service.log_contact(user, lid, payload.note)
    return {"ok": True}


@router.delete("/{lid}")
async def delete_lead(lid: str, user=Depends(forbid_demo_write)):
    await lead_service.delete_lead(user, lid)
    return {"ok": True}
