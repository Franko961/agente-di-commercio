import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET non impostata. Imposta la variabile d'ambiente JWT_SECRET "
        "prima di avviare l'app — è obbligatoria per la sicurezza dei token di accesso."
    )
JWT_ALG = 'HS256'

STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
PAYPAL_WEBHOOK_ID = os.environ.get('PAYPAL_WEBHOOK_ID', '')
PAYPAL_API_BASE = (
    'https://api-m.paypal.com' if PAYPAL_MODE == 'live'
    else 'https://api-m.sandbox.paypal.com'
)

CORS_ORIGINS = [
    origin.strip() for origin in os.environ.get(
        'CORS_ORIGINS',
        'https://salesfly.it,https://www.salesfly.it,https://main--salesfly.netlify.app'
    ).split(',') if origin.strip()
]

TRIAL_DAYS = int(os.environ.get('TRIAL_DAYS', '14'))

PLANS = {
    'base': {
        'name': 'Base',
        'price_eur': 6.00,
        'stripe_price_id': os.environ.get('STRIPE_PRICE_BASE', ''),
        'paypal_plan_id': os.environ.get('PAYPAL_PLAN_BASE', ''),
        'features': [
            'Clienti e anagrafiche illimitati',
            'Agenda e appuntamenti',
            'Offerte e preventivi',
            'Provvigioni e scala premi',
            'Archivio documenti (S3)',
            'Pipeline lead (Kanban)',
            'Mappa clienti geolocalizzata',
            'Assistente AI (50 msg/mese)',
        ],
    },
    'pro': {
        'name': 'Pro',
        'price_eur': 11.00,
        'stripe_price_id': os.environ.get('STRIPE_PRICE_PRO', ''),
        'paypal_plan_id': os.environ.get('PAYPAL_PLAN_PRO', ''),
        'features': [
            'Tutto il piano Base',
            'Assistente AI illimitato',
            'Memoria AI persistente',
            'AI può modificare il CRM',
            'Scala premi avanzata',
            'Statistiche per settore',
            'Esportazione CSV avanzata',
            'Supporto prioritario',
            'Aggiornamenti anticipati',
        ],
    },
}

# --- Motore automazioni ---
# Intervallo tra un ciclo di valutazione e il successivo (controlla tutte le
# automazioni attive di tutti gli utenti). 10 minuti di default: abbastanza
# reattivo per promemoria/scadenze, senza martellare il DB.
AUTOMATION_ENGINE_INTERVAL_SECONDS = int(os.environ.get("AUTOMATION_ENGINE_INTERVAL_SECONDS", str(10 * 60)))
# Dopo questo numero di tentativi falliti consecutivi per lo stesso
# automation+target, si smette di ritentare (l'errore è quasi certamente
# persistente, es. configurazione invalida) e si segna come fallita in modo
# permanente invece di ritentare all'infinito ogni ciclo.
AUTOMATION_MAX_ATTEMPTS = int(os.environ.get("AUTOMATION_MAX_ATTEMPTS", "5"))

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
ADMIN_NOTIFY_EMAIL = os.environ.get("ADMIN_NOTIFY_EMAIL", "franco.bruni.art@gmail.com")
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
S3_ENDPOINT = None if (not _raw_endpoint or "amazonaws.com" in _raw_endpoint) else _raw_endpoint

MAX_FILE_BYTES = 50 * 1024 * 1024

# --- Google Calendar integration ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")
GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
# Dove reindirizzare il browser dopo il callback OAuth (pagina impostazioni del frontend)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://salesfly.it")
