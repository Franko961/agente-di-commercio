from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write, require_module
from services.attendance_service import attendance_service
from models.attendance import AttendanceCorrectionIn

# Gated da "personale", come employee_documents.py/employee_equipment.py:
# le sessioni presenze sono un dato del dipendente, non un modulo a parte.
router = APIRouter(prefix="/api/employees/{eid}/attendance", tags=["attendance"])
MODULE_DEP = Depends(require_module("personale"))


@router.get("", dependencies=[MODULE_DEP])
async def list_attendance(eid: str, user=Depends(get_current_user)):
    return await attendance_service.list_sessions(user, eid)


@router.post("", dependencies=[MODULE_DEP])
async def create_attendance(eid: str, payload: AttendanceCorrectionIn, user=Depends(forbid_demo_write)):
    """Sessione inserita a mano dal responsabile (es. il dipendente ha
    dimenticato di timbrare quel giorno) — marcata corrected_by_admin
    dentro attendance_service.create_manual_session."""
    return await attendance_service.create_manual_session(user, eid, payload)


@router.patch("/{sid}", dependencies=[MODULE_DEP])
async def correct_attendance(eid: str, sid: str, payload: AttendanceCorrectionIn, user=Depends(forbid_demo_write)):
    await attendance_service.correct_session(user, sid, payload)
    return {"ok": True}


@router.delete("/{sid}", dependencies=[MODULE_DEP])
async def delete_attendance(eid: str, sid: str, user=Depends(forbid_demo_write)):
    await attendance_service.delete_session(user, sid)
    return {"ok": True}
