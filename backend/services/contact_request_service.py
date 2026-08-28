import html
import logging

from fastapi import HTTPException

from core.config import CONTACT_NOTIFY_EMAIL
from core.exceptions import ValidationAppError
from core.rate_limit import check_and_record
from core.utils import gen_id, now_iso
from repositories.contact_request_repository import contact_request_repository
from services.email_service import send_email

logger = logging.getLogger(__name__)


class ContactRequestService:
    def __init__(self, repo=contact_request_repository):
        self.repo = repo

    async def create(self, payload, ip_address: str = None) -> dict:
        # Stesso limite anti-abuso già usato per il form richiesta demo (vedi
        # demo_request_service): senza, chiunque potrebbe riempire la casella
        # info@salesfly.it di messaggi automatizzati.
        if ip_address:
            ip_ok = await check_and_record(
                "contact_request_ip", ip_address, max_attempts=5, window_minutes=60
            )
            if not ip_ok:
                raise HTTPException(
                    429, "Troppe richieste da questo indirizzo, riprova più tardi."
                )

        if not payload.privacy_consent:
            raise ValidationAppError(
                "È necessario accettare l'informativa sulla privacy per procedere."
            )

        nome = payload.nome.strip()
        email = payload.email.lower().strip()
        messaggio = payload.messaggio.strip()

        if not nome or not messaggio:
            raise ValidationAppError("Nome e messaggio sono obbligatori.")

        doc = {
            "id": gen_id(),
            "nome": nome,
            "email": email,
            "telefono": (payload.telefono or "").strip(),
            "messaggio": messaggio,
            "ip_address": ip_address,
            "created_at": now_iso(),
        }
        await self.repo.insert(doc)

        await send_email(
            to=CONTACT_NOTIFY_EMAIL,
            subject=f"Nuovo messaggio dal sito — {nome}",
            html=self._admin_email_html(doc),
        )

        return {"ok": True}

    async def list_all(self) -> list:
        return await self.repo.find_many()

    @staticmethod
    def _admin_email_html(doc: dict) -> str:
        # I campi arrivano da un form pubblico non autenticato: vanno sempre
        # HTML-escaped prima di finire nel corpo dell'email, altrimenti un
        # messaggio con markup HTML/script verrebbe interpretato dal client
        # di posta di chi legge (es. Zoho webmail) invece che mostrato come
        # testo semplice.
        nome = html.escape(doc["nome"])
        email = html.escape(doc["email"])
        telefono = html.escape(doc.get("telefono") or "—")
        messaggio = html.escape(doc["messaggio"])
        created_at = html.escape(doc["created_at"])
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; color: #1a1a1a;">
          <h3 style="color:#0A192F;">Nuovo messaggio dal form contatti</h3>
          <table style="width:100%; border-collapse: collapse; font-size: 14px;">
            <tr><td style="padding:4px 0; color:#52525B;">Nome</td><td><strong>{nome}</strong></td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Email</td><td>{email}</td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Telefono</td><td>{telefono}</td></tr>
            <tr><td style="padding:4px 0; color:#52525B;">Data</td><td>{created_at}</td></tr>
          </table>
          <div style="margin-top:16px; padding:12px 16px; background:#F9F9F8; border:1px solid #E4E4E1; border-radius:8px; font-size:14px; white-space:pre-wrap;">{messaggio}</div>
        </div>
        """


contact_request_service = ContactRequestService()
