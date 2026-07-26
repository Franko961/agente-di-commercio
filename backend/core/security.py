import bcrypt
import jwt
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request, Depends
from core.config import JWT_SECRET, JWT_ALG
from core.database import db
from core.subscription_utils import is_subscription_active

# Validità del link "password dimenticata" prima che vada rigenerato.
RESET_TOKEN_TTL_MINUTES = 60

# Validità del link di download firmato per un singolo documento (vedi
# create_document_download_token/decode_document_download_token più sotto):
# breve apposta, il link è pensato per essere usato subito dopo averlo
# richiesto (es. aprire un documento in una nuova scheda), non per essere
# salvato o condiviso.
DOCUMENT_DOWNLOAD_TOKEN_TTL_MINUTES = 5

# Prefissi esenti dal blocco per trial/abbonamento scaduto: l'utente deve
# sempre poter vedere il proprio stato, pagare, o gestire l'account anche
# a prova scaduta. Tutte le altre rotte /api/* vengono bloccate con 402.
TRIAL_GATE_EXEMPT_PREFIXES = (
    "/api/auth",
    "/api/subscription",
    "/api/admin",
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    path = request.url.path
    is_exempt = any(path.startswith(p) for p in TRIAL_GATE_EXEMPT_PREFIXES)
    if not is_exempt and user.get("role") != "admin" and not is_subscription_active(user):
        raise HTTPException(
            status_code=402,
            detail={
                "code": "trial_expired",
                "message": "Il periodo di prova gratuita è scaduto. Attiva un abbonamento per continuare a usare SALESFLY.",
            },
        )
    return user


def create_document_download_token(user_id: str, document_id: str) -> str:
    """Genera un token firmato valido SOLO per scaricare QUESTO documento,
    per QUESTO utente, per pochi minuti — pensato per essere messo in una
    query string (es. un link aperto in una nuova scheda, o incollato in
    un'email), a differenza del token di sessione completo (valido 7 giorni
    per l'intero account) che non deve mai finire in un URL: un URL può
    restare in cronologia del browser, log del server/reverse proxy,
    strumenti di analytics/monitoring, o uno screenshot copiato altrove."""
    payload = {
        "sub": user_id,
        "doc_id": document_id,
        "purpose": "doc_download",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=DOCUMENT_DOWNLOAD_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_document_download_token(token: str, document_id: str) -> str:
    """Verifica il token generato da create_document_download_token: deve
    essere valido, non scaduto, con lo scopo giusto ('doc_download') e
    specifico per QUESTO document_id — un token valido per un altro
    documento viene rifiutato. Ritorna lo user_id se tutto corrisponde,
    solleva jwt.InvalidTokenError altrimenti."""
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    if payload.get("purpose") != "doc_download" or payload.get("doc_id") != document_id:
        raise jwt.InvalidTokenError("Token non valido per questo documento")
    return payload["sub"]


def generate_reset_token() -> tuple:
    """Genera un token di reset password in chiaro (da mandare via email) e il
    suo hash SHA-256 (unico dato salvato su DB): se il DB venisse esposto, il
    token vero e proprio non sarebbe comunque ricavabile. Ritorna anche la
    scadenza (ISO string, UTC)."""
    token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(token)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)).isoformat()
    return token, token_hash, expires_at


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_admin(user: dict) -> bool:
    return user.get("role") == "admin"


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Accesso riservato agli amministratori")
    return user


async def forbid_demo_write(user: dict = Depends(get_current_user)) -> dict:
    """Blocca operazioni distruttive (es. cancellazioni) per l'account demo condiviso."""
    if user.get("is_demo"):
        raise HTTPException(status_code=403, detail="Questa azione non è disponibile nell'account demo")
    return user
