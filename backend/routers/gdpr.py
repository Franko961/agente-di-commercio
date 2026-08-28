from fastapi import APIRouter, Body, Depends, Response

from core.security import clear_auth_cookie, forbid_demo_write, get_current_user
from services.gdpr_service import gdpr_service

router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.get("/export")
async def export_my_data(user=Depends(get_current_user)):
    """Esportazione completa dei dati dell'utente (art. 20 GDPR)."""
    content = await gdpr_service.export_user_data(user)
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="i-miei-dati-salesfly.zip"'
        },
    )


@router.post("/delete-account")
async def delete_my_account(
    response: Response, payload: dict = Body(...), user=Depends(forbid_demo_write)
):
    """Cancellazione definitiva dell'account e di tutti i dati collegati
    (art. 17 GDPR). Richiede la password corrente come conferma."""
    await gdpr_service.delete_account(user, payload.get("password", ""))
    # Come il logout: la sessione non ha più senso dato che l'account non esiste più.
    clear_auth_cookie(response)
    return {"ok": True}
