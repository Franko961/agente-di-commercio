from fastapi import APIRouter, Depends
from core.security import get_current_user, forbid_demo_write, require_module
from services.employee_service import employee_service
from models.employee import EmployeeIn

router = APIRouter(prefix="/api/employees", tags=["employees"])

MODULE_DEP = Depends(require_module("personale"))


@router.get("", dependencies=[MODULE_DEP])
async def list_employees(user=Depends(get_current_user)):
    return await employee_service.list_employees(user)


@router.post("", dependencies=[MODULE_DEP])
async def create_employee(payload: EmployeeIn, user=Depends(forbid_demo_write)):
    return await employee_service.create_employee(user, payload)


@router.put("/{eid}", dependencies=[MODULE_DEP])
async def update_employee(eid: str, payload: EmployeeIn, user=Depends(forbid_demo_write)):
    await employee_service.update_employee(user, eid, payload)
    return {"ok": True}


@router.delete("/{eid}", dependencies=[MODULE_DEP])
async def delete_employee(eid: str, user=Depends(forbid_demo_write)):
    await employee_service.delete_employee(user, eid)
    return {"ok": True}


@router.get("/by-token/{token}")
async def get_employee_by_token(token: str):
    """Pubblico apposta (nessuna dependency di autenticazione/modulo): usato
    dalla pagina di richiesta assenza (frontend/src/pages/RichiediAssenza.jsx)
    per mostrare il nome del dipendente prima ancora di inviare la richiesta,
    senza che il dipendente debba avere un account SalesFly."""
    employee = await employee_service.get_by_token(token)
    return {"name": employee["name"]}
