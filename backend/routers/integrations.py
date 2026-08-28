import logging
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from core.config import FRONTEND_URL
from core.security import forbid_demo_write, get_current_user
from services.google_calendar_service import google_calendar_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations/google", tags=["integrations"])


@router.get("/connect")
async def connect(user=Depends(forbid_demo_write)):
    """Ritorna l'URL a cui reindirizzare il browser per avviare il consenso OAuth Google.

    Bloccato per l'account demo condiviso: un visitatore potrebbe altrimenti
    collegare il proprio account Google REALE, e i suoi eventi reali
    finirebbero sincronizzati nell'account demo condiviso, visibili a
    chiunque altro lo visiti dopo — un leak di dati di terzi, non solo un
    problema di dati demo modificati."""
    return {"auth_url": google_calendar_service.get_auth_url(user["id"])}


@router.get("/callback")
async def callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Google reindirizza qui il browser al termine del consenso (nessuna auth cookie richiesta:
    l'identità dell'utente è nello state firmato generato da /connect)."""
    if error:
        return RedirectResponse(
            f"{FRONTEND_URL}/app/impostazioni?gcal=error&reason={error}"
        )
    if not code or not state:
        return RedirectResponse(
            f"{FRONTEND_URL}/app/impostazioni?gcal=error&reason=missing_params"
        )
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
