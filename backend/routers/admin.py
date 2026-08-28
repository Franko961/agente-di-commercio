from fastapi import APIRouter, Body, Depends, Request, Response

from core.security import (
    IMPERSONATION_TOKEN_TTL_MINUTES,
    get_client_ip,
    require_admin,
    set_auth_cookie,
)
from models.admin import ImpersonateIn
from services.admin_service import admin_service
from services.health_service import health_service

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/auth/make-admin")
async def make_admin(payload: dict = Body(...), request: Request = None):
    """Route temporanea per promuovere un utente ad admin. Richiede ADMIN_SECRET."""
    ip_address = get_client_ip(request) if request else None
    return await admin_service.make_admin(
        payload.get("email", ""), payload.get("secret", ""), ip_address=ip_address
    )


@router.get("/admin/stats")
async def admin_stats(admin=Depends(require_admin)):
    return await admin_service.get_stats()


@router.get("/admin/health")
async def admin_health(hours: int = 24, admin=Depends(require_admin)):
    """Cruscotto di salute applicativa: endpoint lenti, tassi di errore,
    fallimenti/costo delle chiamate AI, email non consegnate,
    sincronizzazioni Google Calendar fallite — nelle ultime `hours` ore."""
    return await health_service.get_health(hours)


@router.get("/admin/audit-log")
async def admin_audit_log(page: int = 1, limit: int = 50, admin=Depends(require_admin)):
    return await admin_service.get_audit_log(page, limit)


@router.get("/admin/users")
async def admin_users(admin=Depends(require_admin), page: int = 1, limit: int = 50):
    return await admin_service.list_users(page, limit)


@router.patch("/admin/users/{uid}")
async def admin_update_user(
    uid: str, payload: dict = Body(...), admin=Depends(require_admin)
):
    await admin_service.update_user(uid, payload, admin=admin)
    return {"ok": True}


@router.delete("/admin/users/{uid}")
async def admin_delete_user(uid: str, admin=Depends(require_admin)):
    await admin_service.delete_user(uid, admin=admin)
    return {"ok": True}


@router.post("/admin/users/{uid}/impersonate")
async def admin_impersonate_user(
    uid: str, response: Response, payload: ImpersonateIn, admin=Depends(require_admin)
):
    """Sostituisce il cookie di sessione dell'admin con uno che autentica
    come l'utente uid, per entrare nel suo gestionale (es. assistenza
    telefonica). Il cookie dell'admin viene sovrascritto, non serve però
    un nuovo login per tornare admin: vedi POST /api/auth/exit-impersonation,
    che usa il claim impersonated_by incorporato in questo stesso token.
    payload.mode "view" è sola lettura, "edit" richiede anche un motivo;
    payload.category è sempre obbligatoria (vedi admin_service.impersonate_user)."""
    token, target_email = await admin_service.impersonate_user(
        uid,
        admin,
        mode=payload.mode,
        reason=payload.reason,
        category=payload.category,
    )
    set_auth_cookie(response, token, max_age=IMPERSONATION_TOKEN_TTL_MINUTES * 60)
    return {"ok": True, "email": target_email}
