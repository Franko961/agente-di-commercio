from fastapi import APIRouter, Request, Depends
from models.contact_request import ContactRequestIn
from services.contact_request_service import contact_request_service
from core.security import require_admin, get_client_ip

router = APIRouter(prefix="/api/contact-requests", tags=["contact-requests"])


@router.post("")
async def create_contact_request(payload: ContactRequestIn, request: Request):
    """Endpoint pubblico (nessuna autenticazione): riceve il form contatti dal
    sito e invia una notifica alla casella info@salesfly.it."""
    ip_address = get_client_ip(request)
    return await contact_request_service.create(payload, ip_address=ip_address)


@router.get("")
async def list_contact_requests(admin=Depends(require_admin)):
    """Elenco dei messaggi ricevuti dal form contatti — riservato agli admin (contiene dati personali)."""
    return await contact_request_service.list_all()
