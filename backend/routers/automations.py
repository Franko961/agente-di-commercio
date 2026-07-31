from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write
from services.automation_service import automation_service
from models.automation import AutomationIn

router = APIRouter(prefix="/api/automations", tags=["automations"])


@router.get("")
async def list_automations(user=Depends(get_current_user)):
    return await automation_service.list_automations(user)


@router.post("")
async def create_automation(payload: AutomationIn, user=Depends(forbid_demo_write)):
    return await automation_service.create_automation(user, payload)


@router.put("/{aid}")
async def update_automation(aid: str, payload: AutomationIn, user=Depends(forbid_demo_write)):
    await automation_service.update_automation(user, aid, payload)
    return {"ok": True}


@router.delete("/{aid}")
async def delete_automation(aid: str, user=Depends(forbid_demo_write)):
    await automation_service.delete_automation(user, aid)
    return {"ok": True}


@router.get("/notifications")
async def list_notifications(unread_only: bool = False, user=Depends(get_current_user)):
    return await automation_service.list_notifications(user, unread_only=unread_only)


@router.put("/notifications/{nid}/read")
async def mark_notification_read(nid: str, user=Depends(get_current_user)):
    await automation_service.mark_notification_read(user, nid)
    return {"ok": True}


@router.get("/{aid}/runs")
async def list_runs(aid: str, user=Depends(get_current_user)):
    return await automation_service.list_runs(user, aid)
