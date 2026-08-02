from fastapi import APIRouter, Depends, Response, Request, HTTPException
from core.security import get_current_user, forbid_demo_write, get_client_ip, create_access_token
from repositories.user_repository import user_repository
from services.auth_service import auth_service
from services.admin_service import admin_service
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


@router.post("/exit-impersonation")
async def exit_impersonation(response: Response, user=Depends(get_current_user)):
    """Torna all'account admin originale senza un nuovo login: legge
    impersonated_by dal token corrente (presente solo se questa è
    davvero una sessione avviata da POST /api/admin/users/{uid}/impersonate,
    vedi core.security.get_current_user) e riemette il normale token da 7
    giorni per quell'admin. Non richiede require_admin: il ruolo corrente
    è quello dell'utente impersonificato, non admin — il controllo giusto
    qui è "questo token ha impersonated_by", non "chi chiama è admin".

    Ricontrolla però che admin_user sia TUTTORA admin: se il ruolo fosse
    stato revocato durante la sessione (caso raro), non deve comunque
    ricevere un token di ritorno senza rifare login — a differenza del
    controllo iniziale in admin_service.impersonate_user (require_admin sul
    router), qui non c'è nessun dependency equivalente a proteggere questo
    passaggio."""
    admin_id = user.get("impersonated_by")
    if not admin_id:
        raise HTTPException(400, "Nessuna sessione di impersonificazione attiva")
    admin_user = await user_repository.find_by_id(admin_id)
    if not admin_user:
        raise HTTPException(404, "Account amministratore non trovato")
    if admin_user.get("role") != "admin":
        raise HTTPException(403, "I permessi di amministratore non sono più validi: effettua un nuovo login")
    token = create_access_token(admin_user["id"], admin_user["email"])
    response.set_cookie("access_token", token, httponly=True, secure=True,
                         samesite="none", max_age=7 * 24 * 3600, path="/")
    await admin_service.record_impersonation_exit(
        admin_user["email"], user["id"], user.get("email"),
        user.get("impersonation_mode", "view"), user.get("impersonation_started_at"),
    )
    return {"ok": True}


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
