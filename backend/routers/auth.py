from fastapi import APIRouter, Depends, Response, Request
from core.security import get_current_user, forbid_demo_write, get_client_ip
from services.auth_service import auth_service
from models.auth import LoginIn, RegisterIn, ForgotPasswordIn, ResetPasswordIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(payload: RegisterIn, response: Response, request: Request):
    ip_address = get_client_ip(request)
    token, out = await auth_service.register(payload, ip_address=ip_address)
    response.set_cookie("access_token", token, httponly=True, secure=True,
                         samesite="none", max_age=7 * 24 * 3600, path="/")
    return out


@router.post("/login")
async def login(payload: LoginIn, response: Response, request: Request):
    ip_address = get_client_ip(request)
    token, out = await auth_service.login(payload, ip_address=ip_address)
    response.set_cookie("access_token", token, httponly=True, secure=True,
                         samesite="none", max_age=7 * 24 * 3600, path="/")
    return out


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    return {"ok": True}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user


@router.post("/onboarding-seen")
async def onboarding_seen(user=Depends(forbid_demo_write)):
    # Bloccato per l'account demo: scrive sul documento utente condiviso
    # (non ripulito dal reset periodico, a differenza delle collection
    # USER_SCOPED_COLLECTIONS), quindi senza questa protezione un solo
    # visitatore che la dismette la nasconderebbe per sempre a tutti i
    # visitatori successivi. Il frontend (AuthContext.jsx) ignora già
    # silenziosamente un eventuale errore qui.
    return await auth_service.mark_onboarding_seen(user)


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordIn, request: Request):
    ip_address = get_client_ip(request)
    return await auth_service.forgot_password(payload, ip_address=ip_address)


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordIn, request: Request):
    ip_address = get_client_ip(request)
    return await auth_service.reset_password(payload, ip_address=ip_address)
