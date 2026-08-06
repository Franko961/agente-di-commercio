from fastapi import APIRouter, Depends, HTTPException, Request
from core.security import get_current_user, forbid_demo_write, require_module, get_client_ip
from core.rate_limit import check_and_record
from services.employee_service import employee_service
from services.leave_request_service import leave_request_service
from services.vehicle_service import vehicle_service
from services.vehicle_deadline_service import vehicle_deadline_service
from services.employee_activity_service import employee_activity_service
from models.employee import EmployeeIn, EmployeeActiveUpdate

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


@router.patch("/{eid}/active", dependencies=[MODULE_DEP])
async def set_employee_active(eid: str, payload: EmployeeActiveUpdate, user=Depends(forbid_demo_write)):
    await employee_service.set_active(user, eid, payload.active)
    return {"ok": True}


@router.post("/{eid}/regenerate-token", dependencies=[MODULE_DEP])
async def regenerate_employee_token(eid: str, user=Depends(forbid_demo_write)):
    """Invalida il link personale corrente del dipendente e ne restituisce
    uno nuovo — vedi employee_service.regenerate_token per il perché
    (token salvato solo come hash, non recuperabile in seguito)."""
    token = await employee_service.regenerate_token(user, eid)
    return {"request_token": token}


@router.delete("/{eid}", dependencies=[MODULE_DEP])
async def delete_employee(eid: str, user=Depends(forbid_demo_write)):
    await employee_service.delete_employee(user, eid)
    return {"ok": True}


@router.get("/{eid}/detail", dependencies=[MODULE_DEP])
async def get_employee_detail(eid: str, user=Depends(get_current_user)):
    """Tutto ciò che serve alla scheda dipendente in una sola chiamata:
    anagrafica, riepilogo ferie/permessi/malattie/KPI (leave_request_service),
    e il mezzo Flotta eventualmente assegnato con la sua prossima revisione
    — quest'ultimo resta None se il modulo Flotta non è in uso, senza far
    fallire la richiesta."""
    employee = await employee_service.get_employee(user, eid)
    summary = await leave_request_service.employee_summary(user, employee)
    vehicle = await vehicle_service.find_assigned(user, eid)
    next_revisione = None
    if vehicle:
        next_revisione = await vehicle_deadline_service.next_deadline(user, vehicle["id"], "revisione")
    return {
        "employee": employee,
        "summary": summary,
        "vehicle": vehicle,
        "next_revisione": next_revisione,
    }


@router.get("/{eid}/activity", dependencies=[MODULE_DEP])
async def get_employee_activity(eid: str, user=Depends(get_current_user)):
    return await employee_activity_service.get_activity(user, eid)


@router.get("/by-token/{token}")
async def get_employee_by_token(token: str, request: Request):
    """Pubblico apposta (nessuna dependency di autenticazione/modulo): usato
    dalla pagina di richiesta assenza (frontend/src/pages/RichiediAssenza.jsx)
    per mostrare il nome del dipendente prima ancora di inviare la richiesta,
    senza che il dipendente debba avere un account SalesFly. Limite per IP:
    senza, chiunque potrebbe martellare l'endpoint provando molti token
    diversi da un unico indirizzo."""
    ip_address = get_client_ip(request)
    ok = await check_and_record("employee_by_token_ip", ip_address, max_attempts=30, window_minutes=60)
    if not ok:
        raise HTTPException(429, "Troppe richieste da questo indirizzo, riprova più tardi.")
    employee = await employee_service.get_by_token(token)
    return {"name": employee["name"]}
