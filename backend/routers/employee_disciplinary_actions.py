from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write, require_module
from services.employee_disciplinary_action_service import employee_disciplinary_action_service
from models.employee_disciplinary_action import EmployeeDisciplinaryActionIn

router = APIRouter(prefix="/api/employees/{eid}/disciplinary-actions", tags=["employee-disciplinary-actions"])
MODULE_DEP = Depends(require_module("personale"))


@router.get("", dependencies=[MODULE_DEP])
async def list_employee_disciplinary_actions(eid: str, user=Depends(get_current_user)):
    return await employee_disciplinary_action_service.list_actions(user, eid)


@router.post("", dependencies=[MODULE_DEP])
async def create_employee_disciplinary_action(eid: str, payload: EmployeeDisciplinaryActionIn, user=Depends(forbid_demo_write)):
    return await employee_disciplinary_action_service.create_action(user, eid, payload)


@router.put("/{aid}", dependencies=[MODULE_DEP])
async def update_employee_disciplinary_action(eid: str, aid: str, payload: EmployeeDisciplinaryActionIn, user=Depends(forbid_demo_write)):
    await employee_disciplinary_action_service.update_action(user, eid, aid, payload)
    return {"ok": True}


@router.delete("/{aid}", dependencies=[MODULE_DEP])
async def delete_employee_disciplinary_action(eid: str, aid: str, user=Depends(forbid_demo_write)):
    await employee_disciplinary_action_service.delete_action(user, eid, aid)
    return {"ok": True}
