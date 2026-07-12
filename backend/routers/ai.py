from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write
from services.ai_service import ai_service
from models.ai import AIQuery

router = APIRouter(prefix="/api/ai", tags=["ai"])


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


@router.get("/suggestions")
async def ai_suggestions(user=Depends(get_current_user)):
    return await ai_service.suggestions(user)
