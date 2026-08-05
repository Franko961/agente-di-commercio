from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write, require_module
from services.automation_service import automation_service
from models.automation import AutomationIn

router = APIRouter(prefix="/api/automations", tags=["automations"])

# Il modulo "automazioni" copre solo le regole (elenco, CRUD, cronologia
# esecuzioni). Le notifiche più sotto restano SEMPRE raggiungibili: la
# campanella delle notifiche è globale (montata in Sidebar.jsx su ogni
# pagina), non solo sulla pagina Automazioni — bloccarla darebbe un
# errore ad ogni caricamento pagina anche per chi ha disattivato solo la
# gestione delle regole.
MODULE_DEP = Depends(require_module("automazioni"))


@router.get("", dependencies=[MODULE_DEP])
async def list_automations(user=Depends(get_current_user)):
    return await automation_service.list_automations(user)


@router.post("", dependencies=[MODULE_DEP])
async def create_automation(payload: AutomationIn, user=Depends(forbid_demo_write)):
    return await automation_service.create_automation(user, payload)


@router.put("/{aid}", dependencies=[MODULE_DEP])
async def update_automation(aid: str, payload: AutomationIn, user=Depends(forbid_demo_write)):
    await automation_service.update_automation(user, aid, payload)
    return {"ok": True}


@router.delete("/{aid}", dependencies=[MODULE_DEP])
async def delete_automation(aid: str, user=Depends(forbid_demo_write)):
    await automation_service.delete_automation(user, aid)
    return {"ok": True}


@router.get("/notifications")
async def list_notifications(unread_only: bool = False, user=Depends(get_current_user)):
    return await automation_service.list_notifications(user, unread_only=unread_only)


@router.put("/notifications/{nid}/read")
async def mark_notification_read(nid: str, user=Depends(forbid_demo_write)):
    await automation_service.mark_notification_read(user, nid)
    return {"ok": True}


@router.get("/{aid}/runs", dependencies=[MODULE_DEP])
async def list_runs(aid: str, user=Depends(get_current_user)):
    return await automation_service.list_runs(user, aid)
