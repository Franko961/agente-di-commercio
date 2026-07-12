from fastapi import APIRouter, Depends, Body
from core.security import require_admin
from services.admin_service import admin_service

router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/auth/make-admin")
async def make_admin(payload: dict = Body(...)):
    """Route temporanea per promuovere un utente ad admin. Richiede ADMIN_SECRET."""
    return await admin_service.make_admin(payload.get("email", ""), payload.get("secret", ""))


@router.get("/admin/stats")
async def admin_stats(admin=Depends(require_admin)):
    return await admin_service.get_stats()


@router.get("/admin/users")
async def admin_users(admin=Depends(require_admin), page: int = 1, limit: int = 50):
    return await admin_service.list_users(page, limit)


@router.patch("/admin/users/{uid}")
async def admin_update_user(uid: str, payload: dict = Body(...), admin=Depends(require_admin)):
    await admin_service.update_user(uid, payload)
    return {"ok": True}


@router.delete("/admin/users/{uid}")
async def admin_delete_user(uid: str, admin=Depends(require_admin)):
    await admin_service.delete_user(uid)
    return {"ok": True}
