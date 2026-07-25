import logging
from core.config import RESEND_API_KEY, APP_FROM_EMAIL
from core.observability import record_event, Timer

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html: str) -> bool:
    """Restituisce True se l'invio è andato a buon fine, False altrimenti —
    prima la funzione non restituiva nulla, quindi chi la chiamava non aveva
    modo di sapere se l'email fosse stata davvero inviata."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY non configurata — email non inviata")
        await record_event("email_send", "failure", to=to, subject=subject, error="RESEND_API_KEY non configurata")
        return False
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        with Timer() as t:
            resend.Emails.send({
                "from": APP_FROM_EMAIL,
                "to": to,
                "subject": subject,
                "html": html,
            })
        logger.info(f"Email inviata a {to}: {subject}")
        await record_event("email_send", "success", to=to, subject=subject, duration_ms=round(t.duration_ms, 1))
        return True
    except Exception as e:
        logger.error(f"Errore invio email a {to}: {e}")
        await record_event("email_send", "failure", to=to, subject=subject, error=str(e)[:300])
        return False
