from fastapi import APIRouter, Body, Depends

from core.security import forbid_demo_write, require_admin
from models.feedback import FeedbackIn
from services.feedback_service import feedback_service

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback")
async def create_feedback(payload: FeedbackIn, user=Depends(forbid_demo_write)):
    return await feedback_service.create(user, payload)


@router.get("/feedback/public")
async def public_feedback():
    """Pubblico, non autenticato: solo i feedback approvati dall'admin E con
    consenso esplicito alla pubblicazione — usato dalla sezione
    testimonianze in home page."""
    return await feedback_service.list_public()


@router.get("/admin/feedback")
async def admin_list_feedback(admin=Depends(require_admin)):
    return await feedback_service.list_all()


@router.patch("/admin/feedback/{fid}")
async def admin_update_feedback(
    fid: str, payload: dict = Body(...), admin=Depends(require_admin)
):
    await feedback_service.set_approved(fid, bool(payload.get("approved", False)))
    return {"ok": True}


@router.delete("/admin/feedback/{fid}")
async def admin_delete_feedback(fid: str, admin=Depends(require_admin)):
    await feedback_service.delete(fid)
    return {"ok": True}
