from fastapi import APIRouter, Depends, Response, Request
from core.security import get_current_user
from services.auth_service import auth_service
from models.auth import LoginIn, RegisterIn, ForgotPasswordIn, ResetPasswordIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(payload: RegisterIn, response: Response, request: Request):
    ip_address = request.client.host if request.client else None
    token, out = await auth_service.register(payload, ip_address=ip_address)
    response.set_cookie("access_token", token, httponly=True, secure=True,
                         samesite="none", max_age=7 * 24 * 3600, path="/")
    return out


@router.post("/login")
async def login(payload: LoginIn, response: Response, request: Request):
    ip_address = request.client.host if request.client else None
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
async def onboarding_seen(user=Depends(get_current_user)):
    return await auth_service.mark_onboarding_seen(user)


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordIn, request: Request):
    ip_address = request.client.host if request.client else None
    return await auth_service.forgot_password(payload, ip_address=ip_address)


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordIn, request: Request):
    ip_address = request.client.host if request.client else None
    return await auth_service.reset_password(payload, ip_address=ip_address)
