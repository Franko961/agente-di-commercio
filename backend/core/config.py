import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

_jwt_secret = os.environ.get("JWT_SECRET")
if not _jwt_secret:
    raise RuntimeError(
        "JWT_SECRET non impostata. Imposta la variabile d'ambiente JWT_SECRET "
        "prima di avviare l'app — è obbligatoria per la sicurezza dei token di accesso."
    )
# Tipizzato esplicitamente str (non Optional[str] come os.environ.get()): il
# controllo sopra garantisce già a runtime che non sia mai None qui in poi —
# senza questa annotazione ogni modulo che importa JWT_SECRET lo vedrebbe
# comunque come Optional[str] per mypy, pur essendo sempre valorizzato.
JWT_SECRET: str = _jwt_secret
JWT_ALG = "HS256"

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox")
PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "")
PAYPAL_API_BASE = (
    "https://api-m.paypal.com"
    if PAYPAL_MODE == "live"
    else "https://api-m.sandbox.paypal.com"
)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "https://salesfly.it,https://www.salesfly.it,https://main--salesfly.netlify.app",
    ).split(",")
    if origin.strip()
]

TRIAL_DAYS = int(os.environ.get("TRIAL_DAYS", "14"))

PLANS = {
    "base": {
        "name": "Base",
        "price_eur": 6.00,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_BASE", ""),
        "paypal_plan_id": os.environ.get("PAYPAL_PLAN_BASE", ""),
        "tagline": "Per gestire il lavoro quotidiano da agente.",
        # Limite reale applicato in ai_service.py (non solo testo descrittivo):
        # None significa nessun limite.
        "ai_monthly_message_limit": 100,
        "features": [
            "Clienti e anagrafiche illimitati",
            "Agenda, appuntamenti e giro visite",
            "Offerte e preventivi",
            "Calcolo provvigioni e scala premi, con soglie personalizzabili",
            "Pipeline lead (Kanban)",
            "Mappa clienti geolocalizzata",
            "Statistiche di vendita per settore/mandante",
            "Archivio documenti",
            "Esportazione dati in CSV",
            "Assistente AI con memoria delle conversazioni e capacità di agire nel CRM, fino a 100 messaggi al mese",
        ],
    },
    "pro": {
        "name": "Pro",
        "price_eur": 11.00,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_PRO", ""),
        "paypal_plan_id": os.environ.get("PAYPAL_PLAN_PRO", ""),
        "tagline": "Tutto il piano Base, con messaggi AI illimitati e accesso anticipato alle novità.",
        "ai_monthly_message_limit": None,
        # Le altre voci elencate qui in precedenza (memoria conversazioni,
        # scrittura CRM via AI, scala premi personalizzata, statistiche per
        # settore/mandante, supporto prioritario) sono state rimosse perché
        # nel codice erano già disponibili a TUTTI i piani (nessun controllo
        # su 'plan' se non qui e nel limite messaggi AI) — restavano solo
        # promesse di marketing senza corrispondenza reale. Se in futuro si
        # decide di renderle davvero esclusive Pro, vanno prima implementati
        # i controlli di piano nel codice, non solo aggiornato questo testo.
        "features": [
            "Assistente AI senza limite di messaggi mensile",
            "Accesso anticipato alle novità",
        ],
    },
}

# Google Calendar: quando il refresh token viene rifiutato da Google (es.
# perche' l'app OAuth e' ancora in modalita' "Test", che fa scadere i token
# dopo ~7 giorni, o perche' l'utente ha revocato l'accesso), evita di
# avvisare l'utente ad ogni ciclo di sync (ogni 5 minuti): un promemoria
# ogni 24 ore e' piu' che sufficiente per fargli notare che deve
# riconnettersi, senza spammargli la casella di posta.
GOOGLE_REAUTH_NOTIFY_COOLDOWN_HOURS = int(
    os.environ.get("GOOGLE_REAUTH_NOTIFY_COOLDOWN_HOURS", "24")
)

# --- OpenRouteService (pianificazione giro visita) ---
# Vuoto di default: senza chiave, il pianificatore usa una stima in linea
# d'aria (haversine) con velocità media assunta, invece di distanze/tempi
# reali su strada. Il piano gratuito di OpenRouteService (2000
# richieste/giorno) è più che sufficiente per un singolo agente — chiave
# gratuita registrabile su openrouteservice.org/dev/#/signup.
ORS_API_KEY = os.environ.get("ORS_API_KEY", "")

# --- Motore automazioni ---
# Intervallo tra un ciclo di valutazione e il successivo (controlla tutte le
# automazioni attive di tutti gli utenti). 10 minuti di default: abbastanza
# reattivo per promemoria/scadenze, senza martellare il DB.
AUTOMATION_ENGINE_INTERVAL_SECONDS = int(
    os.environ.get("AUTOMATION_ENGINE_INTERVAL_SECONDS", str(10 * 60))
)
# Dopo questo numero di tentativi falliti consecutivi per lo stesso
# automation+target, si smette di ritentare (l'errore è quasi certamente
# persistente, es. configurazione invalida) e si segna come fallita in modo
# permanente invece di ritentare all'infinito ogni ciclo.
AUTOMATION_MAX_ATTEMPTS = int(os.environ.get("AUTOMATION_MAX_ATTEMPTS", "5"))

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
# Notifiche operative interne (nuova registrazione, nuova richiesta demo,
# alert di sistema): stessa casella del form contatti, per avere un solo
# punto di arrivo invece di disperderle tra un indirizzo aziendale e uno
# personale.
ADMIN_NOTIFY_EMAIL = os.environ.get("ADMIN_NOTIFY_EMAIL", "info@salesfly.it")
# Casella di posta pubblica (Zoho Mail) dove arrivano i messaggi del form contatti.
CONTACT_NOTIFY_EMAIL = os.environ.get("CONTACT_NOTIFY_EMAIL", "info@salesfly.it")
# Vuoto di default: Sentry resta disattivato finché non si imposta questa
# variabile con il DSN di un account Sentry (anche gratuito).
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
# Vuoto di default: OpenTelemetry resta disattivato finché non si imposta
# l'endpoint OTLP del vendor scelto (es. https://api.honeycomb.io per
# Honeycomb). OTEL_EXPORTER_OTLP_HEADERS (es. "x-honeycomb-team=<api-key>")
# va impostato allo stesso modo, letto automaticamente dall'SDK OTel senza
# bisogno di leggerlo qui.
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "salesfly-backend")
APP_FROM_EMAIL = os.environ.get("APP_FROM_EMAIL", "SALESFLY <noreply@salesfly.it>")

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("S3_REGION", "eu-west-1"))
S3_BUCKET = os.environ.get("AWS_S3_BUCKET", os.environ.get("S3_BUCKET"))
_raw_endpoint = os.environ.get("S3_ENDPOINT", "").strip().strip("[]")
S3_ENDPOINT = (
    None if (not _raw_endpoint or "amazonaws.com" in _raw_endpoint) else _raw_endpoint
)

MAX_FILE_BYTES = 50 * 1024 * 1024

# --- Google Calendar integration ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")
GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
# Dove reindirizzare il browser dopo il callback OAuth (pagina impostazioni del frontend)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://salesfly.it")

# --- Rate limiting dietro reverse proxy ---
# Quanti hop di reverse proxy fidati ci sono davanti all'app: determina
# quale valore di X-Forwarded-For usare come IP del chiamante (vedi
# get_client_ip in core/security.py) invece del solo request.client.host,
# che su Railway è sempre l'IP del proxy stesso, identico per ogni
# visitatore. Default 1: Railway è l'unico proxy che può raggiungere
# davvero il container (nessun altro percorso di rete esiste), quindi è
# l'unico hop di cui ci si può fidare senza verifica aggiuntiva. Se in
# futuro si verifica che anche Netlify aggiunge in modo affidabile il
# proprio hop per il traffico proxato via salesfly.it/api/* (vedi
# frontend/public/_redirects), si può alzare a 2 senza toccare il codice.
TRUSTED_PROXY_HOPS = int(os.environ.get("TRUSTED_PROXY_HOPS", "1"))
