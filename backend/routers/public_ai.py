from fastapi import APIRouter, Request

from core.security import get_client_ip
from models.public_ai_chat import PublicAiChatIn
from services import public_ai_chat_service

router = APIRouter(prefix="/api/public", tags=["public-ai"])


@router.post("/ai-chat")
async def public_ai_chat(payload: PublicAiChatIn, request: Request):
    """Endpoint pubblico (nessuna autenticazione): chat informativa sulla
    homepage, non collegata al CRM — vedi public_ai_chat_service per il
    perché è tenuta separata dall'assistente reale autenticato."""
    ip_address = get_client_ip(request)
    text = await public_ai_chat_service.chat(
        payload.message, payload.history, ip_address
    )
    return {"response": text}
