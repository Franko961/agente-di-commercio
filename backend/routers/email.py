from fastapi import APIRouter, Depends
from core.security import get_current_user
from services.email_log_service import email_log_service
from models.email_log import EmailLogIn

router = APIRouter(prefix="/api/email", tags=["email"])


@router.post("/send")
async def send_email_mock(payload: EmailLogIn, user=Depends(get_current_user)):
    return await email_log_service.send_mock(user, payload)


@router.get("/logs")
async def list_email_logs(user=Depends(get_current_user)):
    return await email_log_service.list_logs(user)
