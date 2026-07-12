import logging
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from core.utils import gen_id, now_iso, clean
from core.security import hash_password, verify_password, create_access_token
from core.config import PLANS, ADMIN_NOTIFY_EMAIL
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
        token = create_access_token(user["id"], email)
        return token, clean(user)


auth_service = AuthService()
