from typing import Optional

from fastapi import APIRouter, Depends

from core.security import forbid_demo_write, get_current_user, require_module
from models.ai import AICancelActionIn, AIExecuteActionIn, AIQuery
from services.ai_service import ai_service

router = APIRouter(
    prefix="/api/ai", tags=["ai"], dependencies=[Depends(require_module("ai"))]
)


@router.get("/history")
async def ai_history(user=Depends(get_current_user)):
    return await ai_service.get_history(user["id"])


@router.delete("/history")
async def clear_ai_history(user=Depends(forbid_demo_write)):
    await ai_service.clear_history(user["id"])
    return {"ok": True}


@router.post("/chat")
async def ai_chat(payload: AIQuery, user=Depends(get_current_user)):
    return await ai_service.chat(user, payload)


@router.post("/execute-action")
async def ai_execute_action(
    payload: AIExecuteActionIn, user=Depends(forbid_demo_write)
):
    """Esegue davvero un'azione economica (vendita/offerta o spesa elevata)
    dopo che l'utente l'ha confermata (eventualmente modificata) sulla scheda
    di conferma mostrata in chat/assistente vocale."""
    return await ai_service.execute_confirmed_action(user, payload.model_dump())


@router.post("/cancel-action")
async def ai_cancel_action(payload: AICancelActionIn, user=Depends(forbid_demo_write)):
    """Segna come annullata un'azione economica proposta dall'AI (scheda di
    conferma) che l'utente ha rifiutato senza registrare nulla sul CRM."""
    return await ai_service.cancel_pending_action(user, payload.log_id)


@router.get("/pending-actions")
async def ai_pending_actions(user=Depends(get_current_user)):
    """Azioni economiche proposte dall'AI (vendite/offerte o spese sopra
    soglia) ancora in attesa di conferma, nel formato atteso da
    AIActionConfirm. Usato per recuperare le schede di conferma dopo un
    refresh, un cambio schermata o la chiusura del pannello vocale."""
    return await ai_service.list_pending_actions(user["id"])


@router.get("/actions")
async def ai_actions(
    tool_name: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 200,
    user=Depends(get_current_user),
):
    """Registro azioni AI (audit log): chi ha fatto cosa attraverso l'assistente,
    con quali parametri e con quale esito. Usato dalla pagina Impostazioni."""
    return await ai_service.list_actions(
        user["id"], tool_name, status, date_from, date_to, limit
    )


@router.get("/briefing")
async def ai_briefing(user=Depends(get_current_user)):
    """Saluto proattivo dell'assistente ('Buongiorno Franco. Hai: ...'),
    mostrato all'apertura della pagina Assistente AI."""
    return await ai_service.get_morning_briefing(user)


@router.get("/suggestions")
async def ai_suggestions(user=Depends(get_current_user)):
    return await ai_service.suggestions(user)
