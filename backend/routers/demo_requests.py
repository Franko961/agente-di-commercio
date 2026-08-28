from fastapi import APIRouter, Depends, Request

from core.security import get_client_ip, require_admin
from models.demo_request import DemoRequestIn
from services.demo_request_service import demo_request_service

router = APIRouter(prefix="/api/demo-requests", tags=["demo-requests"])


@router.post("")
async def create_demo_request(payload: DemoRequestIn, request: Request):
    """Endpoint pubblico (nessuna autenticazione): riceve il form di richiesta demo
    dal sito, salva il consenso con relativa prova (IP, user agent, timestamp,
    versione informativa accettata) e invia le email di conferma."""
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent")
    return await demo_request_service.create(
        payload, ip_address=ip_address, user_agent=user_agent
    )


@router.get("")
async def list_demo_requests(admin=Depends(require_admin)):
    """Elenco delle richieste demo ricevute — riservato agli admin (contiene dati personali)."""
    return await demo_request_service.list_all()
