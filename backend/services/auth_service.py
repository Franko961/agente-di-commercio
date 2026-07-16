import logging
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from core.utils import gen_id, now_iso, clean
from core.security import hash_password, verify_password, create_access_token, generate_reset_token, hash_reset_token
from core.config import PLANS, ADMIN_NOTIFY_EMAIL, FRONTEND_URL
from core.rate_limit import check_and_record
from core.subscription_utils import is_subscription_active
from repositories.user_repository import user_repository
from services.email_service import send_email
from services.seed_service import seed_service

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, repo=user_repository):
        self.repo = repo

    async def register(self, payload) -> dict:
        email = payload.email.lower().strip()
        if await self.repo.find_by_email(email):
            raise HTTPException(status_code=400, detail="Email gia' registrata")
        if len(payload.password) < 6:
            raise HTTPException(status_code=400, detail="Password troppo corta (min 6 caratteri)")
        user_id = gen_id()
        plan = payload.plan if payload.plan in PLANS else "base"
        doc = {
            "id": user_id, "email": email, "name": payload.name,
            "password_hash": hash_password(payload.password),
            "role": "agent", "created_at": now_iso(),
            "plan": plan,
            "subscription_status": "trial",  # trial | active | cancelled | expired
            "trial_ends_at": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "paypal_subscription_id": None,
        }
        await self.repo.insert(doc)

        # Seed starter demo data so the new user lands on a populated app.
        try:
            await seed_service.seed_demo(user_id)
        except Exception as e:
            logger.warning(f"Seed for new user failed: {e}")

        token = create_access_token(user_id, email)

        # Email benvenuto all'utente (non bloccante)
        try:
            await send_email(
                to=email,
                subject="Benvenuto su SALESFLY — il tuo gestionale è pronto!",
                html=f"""
                <div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:32px 24px;background:#F9F9F8;">
                  <div style="background:#0A192F;padding:20px 24px;border-radius:8px;margin-bottom:24px;">
                    <span style="color:#FF5A00;font-weight:900;font-size:22px;letter-spacing:2px;">SALESFLY.</span>
                  </div>
                  <h2 style="color:#0A192F;margin:0 0 12px;">Benvenuto, {doc.get('name', '')}!</h2>
                  <p style="color:#52525B;font-size:15px;line-height:1.6;">
                    Il tuo account è stato creato con successo. Hai <strong>14 giorni di prova gratuita</strong> 
                    per esplorare tutte le funzionalità di SALESFLY.
                  </p>
                  <div style="background:#fff;border:1px solid #E4E4E1;border-radius:8px;padding:20px;margin:24px 0;">
                    <div style="font-size:12px;color:#A1A1AA;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Piano attivo</div>
                    <div style="font-size:20px;font-weight:900;color:#FF5A00;">{plan.upper()} — €{PLANS[plan]['price_eur']:.0f}/mese</div>
                    <div style="font-size:13px;color:#52525B;margin-top:4px;">14 giorni gratuiti, nessuna carta richiesta</div>
                  </div>
                  <a href="https://salesfly.netlify.app" 
                     style="display:inline-block;background:#0A192F;color:#fff;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;">
                    Accedi al gestionale →
                  </a>
                  <p style="color:#A1A1AA;font-size:12px;margin-top:32px;">
                    SALESFLY — Gestionale per agenti di commercio<br>
                    Se non hai creato questo account, ignora questa email.
                  </p>
                </div>
                """
            )
        except Exception as mail_err:
            logger.warning(f"Email benvenuto non inviata: {mail_err}")

        # Email notifica admin (non bloccante)
        try:
            await send_email(
                to=ADMIN_NOTIFY_EMAIL,
                subject=f"🆕 Nuovo utente registrato: {email}",
                html=f"""
                <div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:32px 24px;">
                  <h2 style="color:#0A192F;">Nuovo utente registrato</h2>
                  <table style="width:100%;border-collapse:collapse;font-size:14px;">
                    <tr><td style="padding:8px;color:#52525B;width:120px;">Nome</td><td style="padding:8px;font-weight:600;">{doc.get('name','')}</td></tr>
                    <tr style="background:#F9F9F8;"><td style="padding:8px;color:#52525B;">Email</td><td style="padding:8px;font-weight:600;">{email}</td></tr>
                    <tr><td style="padding:8px;color:#52525B;">Piano</td><td style="padding:8px;font-weight:600;color:#FF5A00;">{plan.upper()}</td></tr>
                    <tr style="background:#F9F9F8;"><td style="padding:8px;color:#52525B;">Data</td><td style="padding:8px;">{now_iso()[:16].replace('T',' ')}</td></tr>
                  </table>
                  <a href="https://salesfly.netlify.app/admin"
                     style="display:inline-block;margin-top:20px;background:#FF5A00;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;">
                    Vedi Admin Dashboard →
                  </a>
                </div>
                """
            )
        except Exception as mail_err:
            logger.warning(f"Email admin non inviata: {mail_err}")

        return token, clean(doc)

    async def login(self, payload) -> tuple:
        email = payload.email.lower()
        user = await self.repo.find_by_email(email)
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Credenziali non valide")
        if user.get("role") != "admin" and not is_subscription_active(user):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "trial_expired",
                    "message": "Il periodo di prova gratuita è scaduto. Attiva un abbonamento per continuare a usare SALESFLY.",
                },
            )
        token = create_access_token(user["id"], email)
        return token, clean(user)

    async def forgot_password(self, payload, ip_address: str = None) -> dict:
        email = payload.email.lower().strip()

        # Risposta generica identica in ogni caso, per non rivelare a chi
        # chiede se un'email è registrata o meno (user enumeration) — usata
        # anche quando si viene bloccati dal rate limit, per lo stesso motivo.
        generic = {
            "ok": True,
            "message": "Se l'indirizzo è registrato, riceverai a breve un'email con le istruzioni per reimpostare la password.",
        }

        # Limite per email: max 5 richieste ogni 15 minuti (evita di intasare
        # di email la stessa casella). Limite per IP: max 20 ogni 15 minuti
        # (evita di usare l'endpoint per scansionare quali email esistono).
        email_ok = await check_and_record("forgot_password_email", email, max_attempts=5, window_minutes=15)
        ip_ok = True
        if ip_address:
            ip_ok = await check_and_record("forgot_password_ip", ip_address, max_attempts=20, window_minutes=15)
        if not email_ok or not ip_ok:
            return generic

        user = await self.repo.find_by_email(email)
        if not user:
            return generic

        token, token_hash, expires_at = generate_reset_token()
        await self.repo.update_by_id(user["id"], {
            "reset_token_hash": token_hash,
            "reset_token_expires": expires_at,
        })
        reset_link = f"{FRONTEND_URL}/reset-password?token={token}"

        try:
            await send_email(
                to=email,
                subject="Reimposta la tua password — SALESFLY",
                html=f"""
                <div style="font-family:sans-serif;max-width:560px;margin:0 auto;padding:32px 24px;background:#F9F9F8;">
                  <div style="background:#0A192F;padding:20px 24px;border-radius:8px;margin-bottom:24px;">
                    <span style="color:#FF5A00;font-weight:900;font-size:22px;letter-spacing:2px;">SALESFLY.</span>
                  </div>
                  <h2 style="color:#0A192F;margin:0 0 12px;">Reimposta la tua password</h2>
                  <p style="color:#52525B;font-size:15px;line-height:1.6;">
                    Abbiamo ricevuto una richiesta di reimpostazione della password per il tuo account SALESFLY.
                    Clicca sul pulsante qui sotto per sceglierne una nuova. Il link è valido per 1 ora.
                  </p>
                  <a href="{reset_link}"
                     style="display:inline-block;background:#0A192F;color:#fff;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;margin:8px 0 24px;">
                    Reimposta password →
                  </a>
                  <p style="color:#A1A1AA;font-size:12px;margin-top:24px;">
                    Se non hai richiesto tu questa email, ignorala pure: la tua password attuale resta invariata.
                  </p>
                </div>
                """
            )
        except Exception as mail_err:
            logger.warning(f"Email reset password non inviata: {mail_err}")

        return generic

    async def reset_password(self, payload, ip_address: str = None) -> dict:
        # Limite per IP: rallenta un eventuale tentativo di indovinare un
        # token per forza bruta (il token stesso, 32 byte casuali, resta
        # comunque non indovinabile in pratica — questo è un livello extra).
        if ip_address:
            ip_ok = await check_and_record("reset_password_ip", ip_address, max_attempts=20, window_minutes=15)
            if not ip_ok:
                raise HTTPException(status_code=429, detail="Troppi tentativi. Riprova tra qualche minuto.")

        if len(payload.new_password) < 6:
            raise HTTPException(status_code=400, detail="Password troppo corta (min 6 caratteri)")

        token_hash = hash_reset_token(payload.token)
        user = await self.repo.find_by_reset_token_hash(token_hash)
        if not user:
            raise HTTPException(status_code=400, detail="Link non valido o già utilizzato")

        expires_raw = user.get("reset_token_expires")
        expires = datetime.fromisoformat(expires_raw) if expires_raw else None
        if not expires or expires < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Il link è scaduto. Richiedine uno nuovo dalla pagina di accesso.")

        await self.repo.update_by_id(user["id"], {
            "password_hash": hash_password(payload.new_password),
            "reset_token_hash": None,
            "reset_token_expires": None,
        })
        return {"ok": True, "message": "Password aggiornata con successo. Ora puoi accedere."}


auth_service = AuthService()
