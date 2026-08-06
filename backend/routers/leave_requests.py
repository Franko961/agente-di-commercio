from typing import Optional
from fastapi import APIRouter, Depends, Request
from core.security import get_current_user, forbid_demo_write, require_module, get_client_ip
from services.leave_request_service import leave_request_service
from models.leave_request import LeaveRequestIn, LeaveRequestDecision, LeaveRequestCertificate

router = APIRouter(prefix="/api/leave-requests", tags=["leave-requests"])

MODULE_DEP = Depends(require_module("personale"))


@router.post("")
async def submit_leave_request(payload: LeaveRequestIn, request: Request):
    """Pubblico apposta (nessuna autenticazione): il dipendente invia la
    richiesta dal proprio link personale (employee_token nel payload),
    senza dover accedere al gestionale — vedi employee_service per come
    viene generato il token."""
    ip_address = get_client_ip(request)
    return await leave_request_service.submit(payload, ip_address=ip_address)


@router.get("", dependencies=[MODULE_DEP])
async def list_leave_requests(status: Optional[str] = None, user=Depends(get_current_user)):
    return await leave_request_service.list_requests(user, status)


@router.patch("/{rid}/decision", dependencies=[MODULE_DEP])
async def decide_leave_request(rid: str, payload: LeaveRequestDecision, user=Depends(forbid_demo_write)):
    await leave_request_service.decide(user, rid, payload.status)
    return {"ok": True}


@router.patch("/{rid}/certificate", dependencies=[MODULE_DEP])
async def set_leave_request_certificate(rid: str, payload: LeaveRequestCertificate, user=Depends(forbid_demo_write)):
    await leave_request_service.set_certificate_received(user, rid, payload.certificate_received)
    return {"ok": True}


@router.delete("/{rid}", dependencies=[MODULE_DEP])
async def delete_leave_request(rid: str, user=Depends(forbid_demo_write)):
    await leave_request_service.delete_request(user, rid)
    return {"ok": True}


@router.get("/calendar", dependencies=[MODULE_DEP])
async def leave_requests_calendar(month: str, user=Depends(get_current_user)):
    """month in formato AAAA-MM."""
    return await leave_request_service.calendar(user, month)


@router.get("/export.csv", dependencies=[MODULE_DEP])
async def export_leave_requests(user=Depends(get_current_user)):
    return await leave_request_service.export_csv(user)
