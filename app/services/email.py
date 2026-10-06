import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger("app.email")


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        if settings.is_production:
            logger.warning("SMTP is not configured; email '%s' was not sent", subject)
        else:
            logger.info("SMTP not configured. Email to %s\nSubject: %s\n%s", to, subject, body)
        return
    message = EmailMessage()
    message["From"] = settings.MAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except Exception:  # never let a mail failure break a request
        logger.exception("Could not send email to %s", to)


def send_reset_email(to: str, token: str) -> None:
    link = f"{settings.cors_origins[0]}{settings.FRONTEND_RESET_PATH}?token={token}"
    send_email(
        to,
        "Reset your Project Progress Platform password",
        f"Use this link to choose a new password. It works once and expires in "
        f"{settings.RESET_TOKEN_MINUTES} minutes:\n\n{link}\n\n"
        "If you did not ask for this, you can ignore this email.",
    )
