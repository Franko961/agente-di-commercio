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

CORS_ORIGINS = [
    origin.strip() for origin in os.environ.get(
        'CORS_ORIGINS',
        'https://salesfly.it,https://www.salesfly.it,https://main--salesfly.netlify.app'
    ).split(',') if origin.strip()
]

PLANS = {
    'base': {'name': 'Base', 'price_eur': 6.00, 'stripe_price_id': os.environ.get('STRIPE_PRICE_BASE', ''), 'paypal_plan_id': os.environ.get('PAYPAL_PLAN_BASE', '')},
    'pro':  {'name': 'Pro',  'price_eur': 11.00, 'stripe_price_id': os.environ.get('STRIPE_PRICE_PRO', ''),  'paypal_plan_id': os.environ.get('PAYPAL_PLAN_PRO', '')},
}

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
ADMIN_NOTIFY_EMAIL = os.environ.get("ADMIN_NOTIFY_EMAIL", "franco.bruni.art@gmail.com")
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
