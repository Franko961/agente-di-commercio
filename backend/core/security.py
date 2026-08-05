import bcrypt
import jwt
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException, Request, Depends
from core.config import JWT_SECRET, JWT_ALG, TRUSTED_PROXY_HOPS
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
    # Diritti GDPR (esportazione/cancellazione dati, vedi routers/gdpr.py):
    # un utente deve poterli esercitare sempre, anche a prova/abbonamento
    # scaduto — altrimenti sarebbe bloccato dal far valere un proprio
    # diritto di legge finché non paga di nuovo.
    "/api/privacy",
)


def get_client_ip(request: Request) -> Optional[str]:
    """IP del chiamante da usare per il rate limiting (login, registrazione,
    richieste demo/contatti — vedi core/rate_limit.py), al netto del reverse
    proxy davanti all'app: request.client.host da solo è SEMPRE l'IP di
    Railway stesso, identico per ogni singolo visitatore — con quello come
    chiave, un limite di "5 richieste" varrebbe per TUTTI gli utenti messi
    insieme, non per singolo visitatore.

    X-Forwarded-For viene però scritto lungo la catena da chiunque si
    connetta, incluso un chiamante diretto e malevolo che può impostarlo a
    piacere: fidarsi ciecamente della prima voce permetterebbe di aggirare
    il rate limit a piacimento (basta cambiare valore ad ogni richiesta).
    L'unica voce non falsificabile è quella aggiunta dal proxy con cui
    l'app comunica DIRETTAMENTE — Railway, l'unico modo in cui una
    richiesta può fisicamente raggiungere il container — quindi si prende
    l'N-esima voce da destra, dove N = TRUSTED_PROXY_HOPS (vedi
    core/config.py), mai la prima della lista."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        hops = [h.strip() for h in xff.split(",") if h.strip()]
        if TRUSTED_PROXY_HOPS >= 1 and len(hops) >= TRUSTED_PROXY_HOPS:
            return hops[-TRUSTED_PROXY_HOPS]
    return request.client.host if request.client else None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


# Più breve dei 7 giorni del token normale apposta: una sessione di
# impersonificazione dimenticata aperta (es. una scheda del browser mai
# chiusa) deve scadere da sola in tempi brevi, non restare valida per una
# settimana con accesso completo ai dati di un altro utente.
IMPERSONATION_TOKEN_TTL_MINUTES = 60


def create_impersonation_token(admin_id: str, target_user_id: str, target_email: str, mode: str = "view") -> str:
    """Token che fa autenticare il chiamante COME target_user_id, con in più
    il claim impersonated_by: è quel claim (letto da get_current_user sotto)
    a rendere possibile tornare all'account admin originale senza dover
    rifare login (vedi /api/auth/exit-impersonation in routers/auth.py).
    mode è "view" (default, sola lettura — vedi forbid_demo_write più sotto,
    che blocca le scritture anche in questa modalità) oppure "edit" (accesso
    in scrittura, richiede un motivo — vedi admin_service.impersonate_user).
    iat viene incluso esplicitamente (PyJWT lo converte in timestamp Unix da
    solo) per poter calcolare la durata della sessione quando termina — vedi
    admin_service.record_impersonation_exit."""
    payload = {
        "sub": target_user_id, "email": target_email, "type": "access",
        "impersonated_by": admin_id, "impersonation_mode": mode,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=IMPERSONATION_TOKEN_TTL_MINUTES),
    }
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

    # Presente solo nei token di impersonificazione (vedi
    # create_impersonation_token): propagato qui, non solo letto al volo
    # nell'endpoint di uscita, così ogni risposta che include l'utente
    # (es. /api/auth/me) porta con sé l'informazione — è quello che permette
    # al frontend di mostrare sempre il banner "stai impersonificando X",
    # non solo nella pagina dove è iniziata la sessione.
    if payload.get("impersonated_by"):
        user["impersonated_by"] = payload["impersonated_by"]
        user["impersonation_mode"] = payload.get("impersonation_mode", "view")
        if payload.get("iat"):
            user["impersonation_started_at"] = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

    path = request.url.path
    is_exempt = any(path.startswith(p) for p in TRIAL_GATE_EXEMPT_PREFIXES)
    # Una sessione di impersonificazione (payload.impersonated_by presente)
    # è sempre esente dal gate, indipendentemente dal ruolo dell'utente
    # impersonificato: l'admin sta entrando per assistenza, non deve essere
    # bloccato dallo stato di abbonamento (scaduto/annullato) proprio
    # dell'utente che sta aiutando — anzi è spesso proprio il motivo per cui
    # serve assistenza. Non riguarda l'utente impersonificato quando accede
    # con il proprio login normale (lì il token non porta questo claim).
    if not is_exempt and not payload.get("impersonated_by") and user.get("role") != "admin" and not is_subscription_active(user):
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


# Moduli disattivabili per singolo account (vedi admin_service.py per
# l'endpoint che li imposta, Admin.jsx per l'interfaccia). Dashboard,
# Impostazioni e Abbonamento non sono in elenco: restano sempre attivi,
# altrimenti un utente con tutto disattivato non potrebbe più navigare
# l'app né riattivarsi da solo un modulo.
MODULE_KEYS = (
    "clienti", "lead", "agenda", "mappa", "offerte", "ordini",
    "provvigioni", "spese", "mandanti", "prodotti", "documenti",
    "automazioni", "ai",
)

# Moduli verticali costruiti per un cliente specifico (es. CACI SRL), non
# pertinenti a un normale agente di commercio plurimandatario: a differenza
# di MODULE_KEYS sopra (attivi di default, disattivabili per singolo
# account), questi partono SPENTI per tutti e vanno accesi esplicitamente
# — vedi enabled_extra_modules sul documento utente, impostato da Admin.jsx.
EXTRA_MODULE_KEYS = (
    "personale",
    "flotta",
)


def module_enabled(user: dict, module: str) -> bool:
    """Stessa logica di require_module qui sotto, ma richiamabile anche
    fuori da un Depends() FastAPI — serve per verificare il modulo del
    PROPRIETARIO di una risorsa, non dell'utente autenticato: gli
    endpoint pubblici del modulo Personale (routers/employees.py
    GET /by-token, routers/leave_requests.py POST) non hanno una sessione
    autenticata da cui passare per require_module, ma devono comunque
    rifiutare l'accesso se il proprietario ha nel frattempo disattivato
    il modulo (vedi employee_service.get_by_token,
    leave_request_service.submit)."""
    if module in EXTRA_MODULE_KEYS:
        return module in (user.get("enabled_extra_modules") or [])
    return module not in (user.get("disabled_modules") or [])


def require_module(module: str):
    """Dependency factory da passare a APIRouter(dependencies=[...]) per
    bloccare l'intero router se quel modulo non è disponibile per
    l'utente. A differenza del semplice nascondere la voce di menu in
    sidebar, questo impedisce anche di raggiungere l'API direttamente."""
    async def _check(user: dict = Depends(get_current_user)) -> dict:
        if not module_enabled(user, module):
            raise HTTPException(status_code=403, detail=f"Il modulo \"{module}\" non è disponibile per questo account.")
        return user
    return _check


async def forbid_demo_write(user: dict = Depends(get_current_user)) -> dict:
    """Blocca qualunque scrittura (creazione, modifica, cancellazione) per
    l'account demo condiviso, ED ANCHE per un admin che sta impersonificando
    un utente in modalità "view" (sola lettura, vedi create_impersonation_token):
    è la dependency da usare su OGNI rotta POST/PUT/PATCH/DELETE che modifica
    dati appartenenti all'utente, non solo su quelle distruttive — sia
    l'account demo sia una sessione di impersonificazione in sola lettura
    sono pensati per essere esplorabili senza poter scrivere (vedi
    services/demo_reset_service.py per la strategia demo completa)."""
    if user.get("is_demo"):
        raise HTTPException(status_code=403, detail="Questa azione non è disponibile nell'account demo")
    if user.get("impersonation_mode") == "view":
        raise HTTPException(status_code=403, detail="Modalità sola lettura: passa a \"Accedi e modifica\" per apportare modifiche")
    return user
