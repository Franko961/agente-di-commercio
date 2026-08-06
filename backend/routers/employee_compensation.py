from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write, require_module
from services.employee_compensation_service import employee_compensation_service
from models.employee_compensation import EmployeeCompensationIn

router = APIRouter(prefix="/api/employees/{eid}/compensation", tags=["employee-compensation"])
MODULE_DEP = Depends(require_module("personale"))


@router.get("", dependencies=[MODULE_DEP])
async def list_employee_compensation(eid: str, user=Depends(get_current_user)):
    return await employee_compensation_service.list_compensations(user, eid)


@router.post("", dependencies=[MODULE_DEP])
async def create_employee_compensation(eid: str, payload: EmployeeCompensationIn, user=Depends(forbid_demo_write)):
    return await employee_compensation_service.create_compensation(user, eid, payload)


@router.put("/{cid}", dependencies=[MODULE_DEP])
async def update_employee_compensation(eid: str, cid: str, payload: EmployeeCompensationIn, user=Depends(forbid_demo_write)):
    await employee_compensation_service.update_compensation(user, cid, payload)
    return {"ok": True}


@router.delete("/{cid}", dependencies=[MODULE_DEP])
async def delete_employee_compensation(eid: str, cid: str, user=Depends(forbid_demo_write)):
    await employee_compensation_service.delete_compensation(user, cid)
    return {"ok": True}
