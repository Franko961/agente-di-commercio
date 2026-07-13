import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from core.security import get_current_user
from core.config import FRONTEND_URL
from services.google_calendar_service import google_calendar_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations/google", tags=["integrations"])


@router.get("/connect")
async def connect(user=Depends(get_current_user)):
    """Ritorna l'URL a cui reindirizzare il browser per avviare il consenso OAuth Google."""
    return {"auth_url": google_calendar_service.get_auth_url(user["id"])}


@router.get("/callback")
async def callback(code: str = None, state: str = None, error: str = None):
    """Google reindirizza qui il browser al termine del consenso (nessuna auth cookie richiesta:
    l'identità dell'utente è nello state firmato generato da /connect)."""
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/app/impostazioni?gcal=error&reason={error}")
    if not code or not state:
        return RedirectResponse(f"{FRONTEND_URL}/app/impostazioni?gcal=error&reason=missing_params")
    try:
        await google_calendar_service.handle_oauth_callback(code, state)
    except ValueError as e:
        logger.error(f"Callback Google Calendar fallito: {e}")
        return RedirectResponse(f"{FRONTEND_URL}/app/impostazioni?gcal=error")
    return RedirectResponse(f"{FRONTEND_URL}/app/impostazioni?gcal=connected")


@router.post("/disconnect")
async def disconnect(user=Depends(get_current_user)):
    await google_calendar_service.disconnect(user["id"])
    return {"ok": True}


@router.get("/status")
async def status(user=Depends(get_current_user)):
    return await google_calendar_service.get_status(user["id"])


@router.post("/sync")
async def sync_now(user=Depends(get_current_user)):
    """Trigger manuale di sincronizzazione (oltre al polling periodico in background)."""
    await google_calendar_service.sync_now(user["id"])
    return {"ok": True}
