from fastapi import APIRouter, Depends, Request

from core.security import (
    forbid_demo_write,
    get_client_ip,
    get_current_user,
    require_module,
)
from models.attendance import AttendanceCorrectionIn, AttendanceKioskClockIn
from services.attendance_service import attendance_service

# Gated da "personale", come employee_documents.py/employee_equipment.py:
# le sessioni presenze sono un dato del dipendente, non un modulo a parte.
router = APIRouter(prefix="/api/employees/{eid}/attendance", tags=["attendance"])
MODULE_DEP = Depends(require_module("personale"))


@router.get("", dependencies=[MODULE_DEP])
async def list_attendance(eid: str, user=Depends(get_current_user)):
    return await attendance_service.list_sessions(user, eid)


@router.post("", dependencies=[MODULE_DEP])
async def create_attendance(
    eid: str, payload: AttendanceCorrectionIn, user=Depends(forbid_demo_write)
):
    """Sessione inserita a mano dal responsabile (es. il dipendente ha
    dimenticato di timbrare quel giorno) — marcata corrected_by_admin
    dentro attendance_service.create_manual_session."""
    return await attendance_service.create_manual_session(user, eid, payload)


@router.patch("/{sid}", dependencies=[MODULE_DEP])
async def correct_attendance(
    eid: str, sid: str, payload: AttendanceCorrectionIn, user=Depends(forbid_demo_write)
):
    await attendance_service.correct_session(user, eid, sid, payload)
    return {"ok": True}


@router.delete("/{sid}", dependencies=[MODULE_DEP])
async def delete_attendance(eid: str, sid: str, user=Depends(forbid_demo_write)):
    await attendance_service.delete_session(user, eid, sid)
    return {"ok": True}


# Account-level (non per singolo dipendente): router separato, non sotto
# il prefix "/api/employees/{eid}/attendance" sopra, altrimenti "calendar"
# verrebbe interpretato come un {eid} letterale.
account_router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@account_router.get("/calendar", dependencies=[MODULE_DEP])
async def get_attendance_calendar(month: str, user=Depends(get_current_user)):
    """month in formato AAAA-MM. Ore lavorate per dipendente/giorno, per
    la griglia di gruppo (Personale → Calendario) accanto alle assenze
    già mostrate da GET /leave-requests/calendar."""
    return await attendance_service.calendar(user, month)


@account_router.get("/expected", dependencies=[MODULE_DEP])
async def get_attendance_expected(month: str, user=Depends(get_current_user)):
    """month in formato AAAA-MM. Ore ATTESE per dipendente/giorno,
    calcolate dall'orario contrattuale — per il confronto con le ore reali
    di GET /calendar nella griglia di gruppo, vedi attendance_service.expected_hours."""
    return await attendance_service.expected_hours(user, month)


@account_router.get("/today-summary", dependencies=[MODULE_DEP])
async def get_attendance_today_summary(user=Depends(get_current_user)):
    """Widget 'Presenze oggi' della Dashboard: quanti dipendenti attesi in
    turno oggi hanno già timbrato, vedi attendance_service.today_summary."""
    return await attendance_service.today_summary(user)


@account_router.get("/export.xlsx", dependencies=[MODULE_DEP])
async def export_attendance(month: str, user=Depends(get_current_user)):
    """month in formato AAAA-MM. Cartellino del mese (timbrature + assenze
    approvate) per il consulente del lavoro, vedi attendance_service.export_xlsx."""
    return await attendance_service.export_xlsx(user, month)


# Chiosco pubblico: QR fisico uguale per tutti i dipendenti, affisso
# all'ingresso dell'azienda (vedi il docstring di AttendanceService per
# il perché di questa scelta invece del link personale). Router separato,
# senza il prefix "/api/employees/{eid}/..." sopra: qui non c'è un eid
# nell'URL, solo il token azienda — vedi attendance_service.list_kiosk_employees
# e clock_in_kiosk/clock_out_kiosk.
kiosk_router = APIRouter(prefix="/api/attendance/kiosk", tags=["attendance"])


@kiosk_router.get("/{token}/employees")
async def list_kiosk_employees(token: str):
    return await attendance_service.list_kiosk_employees(token)


@kiosk_router.post("/{token}/clock-in")
async def kiosk_clock_in(token: str, payload: AttendanceKioskClockIn, request: Request):
    ip_address = get_client_ip(request)
    return await attendance_service.clock_in_kiosk(
        token, payload.employee_id, payload.pin, ip_address=ip_address
    )


@kiosk_router.post("/{token}/clock-out")
async def kiosk_clock_out(
    token: str, payload: AttendanceKioskClockIn, request: Request
):
    ip_address = get_client_ip(request)
    return await attendance_service.clock_out_kiosk(
        token, payload.employee_id, payload.pin, ip_address=ip_address
    )
