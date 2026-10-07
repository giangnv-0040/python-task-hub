import logging
import smtplib
from email.message import EmailMessage

from app.config import settings
from app.core.constants import SMTP_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    """Gui mail dong bo qua SMTP (Mailpit khi dev). Chi goi tu Celery task
    (worker thread), khong goi truc tiep tu request handler (block event loop)."""
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(
        settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT_SECONDS
    ) as client:
        if settings.smtp_use_tls:
            client.starttls()
        if settings.smtp_user:
            client.login(settings.smtp_user, settings.smtp_password or "")
        client.send_message(message)
    logger.info("Sent email to %s: %s", to, subject)
