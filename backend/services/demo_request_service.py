from core.utils import gen_id, now_iso
from core.exceptions import ValidationAppError
from core.config import FRONTEND_URL, ADMIN_NOTIFY_EMAIL
from repositories.demo_request_repository import demo_request_repository
from services.email_service import send_email

# Versione dell'informativa privacy accettata al momento dell'invio del form.
# Va incrementata ogni volta che il testo dell'informativa cambia in modo sostanziale,
# così restano tracciate le condizioni esatte accettate da ciascun utente nel tempo.
PRIVACY_POLICY_VERSION = "1.0-2026-07-14"


class DemoRequestService:
    def __init__(self, repo=demo_request_repository):
        self.repo = repo

    async def create(self, payload, ip_address: str = None, user_agent: str = None) -> dict:
        if not payload.privacy_consent:
            raise ValidationAppError(
                "È necessario accettare l'informativa sulla privacy per procedere."
            )

        nome = payload.nome.strip()
        cognome = payload.cognome.strip()
        email = payload.email.lower().strip()

        if not nome or not cognome:
            raise ValidationAppError("Nome e cognome sono obbligatori.")

        doc = {
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
        }
        await self.repo.insert(doc)

        demo_link = f"{FRONTEND_URL}/login?demo=auto"

        await send_email(
            to=email,
            subject="Il tuo accesso alla demo di SALESFLY",
            html=self._user_email_html(nome, demo_link),
        )
        await send_email(
            to=ADMIN_NOTIFY_EMAIL,
            subject=f"Nuova richiesta demo — {nome} {cognome}",
            html=self._admin_email_html(doc),
        )

        return {"ok": True}

    async def list_all(self) -> list:
        return await self.repo.find_many()

    @staticmethod
    def _user_email_html(nome: str, demo_link: str) -> str:
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; color: #1a1a1a;">
          <h2 style="color:#0A192F;">Ciao {nome},</h2>
          <p>Grazie per aver richiesto l'accesso alla demo di <strong>SALESFLY</strong>,
          il CRM pensato per gli agenti di commercio.</p>
          <p>Puoi accedere subito cliccando sul pulsante qui sotto:</p>
          <p style="text-align:center; margin: 32px 0;">
            <a href="{demo_link}"
               style="background:#0A192F; color:#ffffff; text-decoration:none;
                      padding: 12px 24px; border-radius: 6px; font-weight: bold;
                      display:inline-block;">
              Entra nella demo
            </a>
          </p>
          <p style="font-size: 13px; color: #52525B;">
            Se il pulsante non funziona, copia e incolla questo link nel browser:<br/>
            <a href="{demo_link}">{demo_link}</a>
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
        </div>
        """


demo_request_service = DemoRequestService()
