import logging
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException

from core.utils import gen_id, now_iso
from core.security import hash_password
from core.exceptions import ValidationAppError
from core.config import FRONTEND_URL, ADMIN_NOTIFY_EMAIL, TRIAL_DAYS
from core.rate_limit import check_and_record
from repositories.demo_request_repository import demo_request_repository
from repositories.user_repository import user_repository
from services.email_service import send_email
from services.seed_service import seed_service

logger = logging.getLogger(__name__)

# Versione dell'informativa privacy accettata al momento dell'invio del form.
# Va incrementata ogni volta che il testo dell'informativa cambia in modo sostanziale,
# così restano tracciate le condizioni esatte accettate da ciascun utente nel tempo.
PRIVACY_POLICY_VERSION = "1.0-2026-07-14"

TRIAL_PLAN = "base"  # piano assegnato di default all'account di prova creato dal form demo


def _generate_password(length: int = 10) -> str:
    """Genera una password casuale leggibile (senza caratteri ambigui come 0/O/1/l)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class DemoRequestService:
    def __init__(self, repo=demo_request_repository, users=user_repository):
        self.repo = repo
        self.users = users

    async def create(self, payload, ip_address: str = None, user_agent: str = None) -> dict:
        # Endpoint pubblico non autenticato che crea un account VERO e
        # funzionante (con dati demo già seminati) e manda una password reale
        # via email all'indirizzo indicato: senza un limite di frequenza,
        # chiunque potrebbe scriptare la creazione di account fasulli in
        # massa e/o far ricevere a indirizzi altrui email di "credenziali"
        # non richieste — oltre al costo/rischio reputazionale sull'invio
        # email. Limite per IP (non per email: un attaccante userebbe email
        # sempre diverse, è l'IP a doversi arginare), stesso principio già
        # applicato a forgot-password in auth_service.
        if ip_address:
            ip_ok = await check_and_record("demo_request_ip", ip_address, max_attempts=5, window_minutes=60)
            if not ip_ok:
                raise HTTPException(429, "Troppe richieste da questo indirizzo, riprova più tardi.")

        if not payload.privacy_consent:
            raise ValidationAppError(
                "È necessario accettare l'informativa sulla privacy per procedere."
            )

        nome = payload.nome.strip()
        cognome = payload.cognome.strip()
        email = payload.email.lower().strip()

        if not nome or not cognome:
            raise ValidationAppError("Nome e cognome sono obbligatori.")

        existing_user = await self.users.find_by_email(email)
        if existing_user:
            raise ValidationAppError(
                "Esiste già un account con questa email. Accedi con le tue credenziali "
                "oppure, se le hai dimenticate, contattaci."
            )

        # Crea subito un account reale e a tempo (TRIAL_DAYS giorni di prova), con
        # credenziali proprie inviate via email — non più un accesso condiviso.
        password = _generate_password()
        user_id = gen_id()
        user_doc = {
            "id": user_id,
            "email": email,
            "name": f"{nome} {cognome}",
            "password_hash": hash_password(password),
            "role": "agent",
            "created_at": now_iso(),
            "plan": TRIAL_PLAN,
            "subscription_status": "trial",
            "trial_ends_at": (datetime.now(timezone.utc) + timedelta(days=TRIAL_DAYS)).isoformat(),
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "paypal_subscription_id": None,
        }
        await self.users.insert(user_doc)

        try:
            await seed_service.seed_demo(user_id)
        except Exception as e:
            logger.warning(f"Seed dati demo per richiesta demo fallito: {e}")

        demo_request_doc = {
            "id": gen_id(),
            "nome": nome,
            "cognome": cognome,
            "email": email,
            "azienda": (payload.azienda or "").strip(),
            "telefono": (payload.telefono or "").strip(),
            "privacy_consent": True,
            "privacy_consent_at": now_iso(),
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
            "marketing_consent": bool(payload.marketing_consent),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": now_iso(),
            "user_id": user_id,
        }
        await self.repo.insert(demo_request_doc)

        login_link = f"{FRONTEND_URL}/login"

        await send_email(
            to=email,
            subject=f"Le tue credenziali di accesso a SALESFLY — {TRIAL_DAYS} giorni di prova",
            html=self._user_email_html(nome, email, password, login_link),
        )
        await send_email(
            to=ADMIN_NOTIFY_EMAIL,
            subject=f"Nuova richiesta demo — {nome} {cognome}",
            html=self._admin_email_html(demo_request_doc),
        )

        return {"ok": True}

    async def list_all(self) -> list:
        return await self.repo.find_many()

    @staticmethod
    def _user_email_html(nome: str, email: str, password: str, login_link: str) -> str:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; color: #1a1a1a;">
          <h2 style="color:#0A192F;">Ciao {nome},</h2>
          <p>Grazie per aver richiesto l'accesso a <strong>SALESFLY</strong>,
          il CRM pensato per gli agenti di commercio. Abbiamo creato il tuo account
          con <strong>{TRIAL_DAYS} giorni di prova gratuita</strong>, nessuna carta richiesta.</p>
          <div style="background:#F9F9F8; border:1px solid #E4E4E1; border-radius:8px; padding:16px 20px; margin:24px 0;">
            <div style="font-size:12px; color:#52525B; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Le tue credenziali</div>
            <div style="font-size:14px; margin-bottom:6px;"><strong>Email:</strong> {email}</div>
            <div style="font-size:14px;"><strong>Password:</strong> {password}</div>
          </div>
          <p style="font-size:13px; color:#52525B;">Ti consigliamo di cambiare la password dopo il primo accesso, dalle impostazioni del tuo profilo.</p>
          <p style="text-align:center; margin: 32px 0;">
            <a href="{login_link}"
               style="background:#0A192F; color:#ffffff; text-decoration:none;
                      padding: 12px 24px; border-radius: 6px; font-weight: bold;
                      display:inline-block;">
              Accedi a SALESFLY
            </a>
          </p>
          <p style="font-size: 13px; color: #52525B;">
            Se il pulsante non funziona, copia e incolla questo link nel browser:<br/>
            <a href="{login_link}">{login_link}</a>
          </p>
          <hr style="border:none; border-top:1px solid #E4E4E1; margin: 24px 0;" />
          <p style="font-size: 12px; color: #999;">
            SALESFLY — Gestionale per Agenti di Commercio · salesfly.it<br/>
            Hai ricevuto questa email perché hai richiesto tu stesso l'accesso alla demo
            tramite il modulo su salesfly.it. Per informazioni sul trattamento dei tuoi dati
            consulta la nostra <a href="https://salesfly.it/privacy">informativa privacy</a>.
          </p>
        </div>
        """

    @staticmethod
    def _admin_email_html(doc: dict) -> str:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; color: #1a1a1a;">
          <h3 style="color:#0A192F;">Nuova richiesta di accesso demo</h3>
          <table style="width:100%; border-collapse: collapse; font-size: 14px;">
            <tr><td style="padding:4px 0; color:#52525B;">Nome</td><td><strong>{doc['nome']} {doc['cognome']}</strong></td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Email</td><td>{doc['email']}</td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Azienda</td><td>{doc.get('azienda') or '—'}</td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Telefono</td><td>{doc.get('telefono') or '—'}</td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Consenso marketing</td><td>{'Sì' if doc.get('marketing_consent') else 'No'}</td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Data</td><td>{doc['created_at']}</td></tr>
          </table>
          <p style="font-size:13px; color:#52525B; margin-top:16px;">
            È stato creato automaticamente un account di prova ({TRIAL_DAYS} giorni) per questo utente.
          </p>
        </div>
        """


demo_request_service = DemoRequestService()
