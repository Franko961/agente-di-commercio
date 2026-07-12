import logging
from core.config import RESEND_API_KEY, APP_FROM_EMAIL

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html: str):
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY non configurata — email non inviata")
        return
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": APP_FROM_EMAIL,
            "to": to,
            "subject": subject,
            "html": html,
        })
        logger.info(f"Email inviata a {to}: {subject}")
    except Exception as e:
        logger.error(f"Errore invio email a {to}: {e}")
