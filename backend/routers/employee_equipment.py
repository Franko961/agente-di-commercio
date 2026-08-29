from fastapi import APIRouter, Depends

from core.security import forbid_demo_write, get_current_user, require_module
from models.employee_equipment import EmployeeEquipmentIn
from services.employee_equipment_service import employee_equipment_service

router = APIRouter(prefix="/api/employees/{eid}/equipment", tags=["employee-equipment"])
MODULE_DEP = Depends(require_module("personale"))


@router.get("", dependencies=[MODULE_DEP])
async def list_employee_equipment(eid: str, user=Depends(get_current_user)):
    return await employee_equipment_service.list_equipment(user, eid)


@router.post("", dependencies=[MODULE_DEP])
async def create_employee_equipment(
    eid: str, payload: EmployeeEquipmentIn, user=Depends(forbid_demo_write)
):
    return await employee_equipment_service.create_equipment(user, eid, payload)


@router.put("/{eqid}", dependencies=[MODULE_DEP])
async def update_employee_equipment(
    eid: str, eqid: str, payload: EmployeeEquipmentIn, user=Depends(forbid_demo_write)
):
    await employee_equipment_service.update_equipment(user, eid, eqid, payload)
    return {"ok": True}


@router.delete("/{eqid}", dependencies=[MODULE_DEP])
async def delete_employee_equipment(
    eid: str, eqid: str, user=Depends(forbid_demo_write)
):
    await employee_equipment_service.delete_equipment(user, eid, eqid)
    return {"ok": True}
