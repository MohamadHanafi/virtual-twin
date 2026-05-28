import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from dotenv import load_dotenv

from app.constants.email import (
    CONTACT_EMAIL_HEADER,
    CONTACT_EMAIL_SESSION_LABEL,
    CONTACT_EMAIL_SUBJECT_PREFIX,
    CONTACT_TO_EMAIL_ENV,
    DEFAULT_SMTP_PORT,
    DEFAULT_SMTP_USE_TLS,
    EMAIL_SEND_FAILURE_MESSAGE,
    EMAIL_SEND_TIMEOUT_SECONDS,
    INVALID_SMTP_PORT_MESSAGE,
    SMTP_FROM_EMAIL_ENV,
    SMTP_HOST_ENV,
    SMTP_PASSWORD_ENV,
    SMTP_PORT_ENV,
    SMTP_USERNAME_ENV,
    SMTP_USE_TLS_ENV,
)
from app.constants.paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")


class EmailServiceError(Exception):
    pass


@dataclass(frozen=True)
class ContactEmail:
    name: str
    email: str
    content: str
    session_id: str


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise EmailServiceError(f"{name} is required to send contact emails")
    return value


def _smtp_port() -> int:
    value = os.getenv(SMTP_PORT_ENV, DEFAULT_SMTP_PORT).strip()
    try:
        return int(value)
    except ValueError as exc:
        raise EmailServiceError(INVALID_SMTP_PORT_MESSAGE) from exc


def _smtp_use_tls() -> bool:
    value = os.getenv(SMTP_USE_TLS_ENV, DEFAULT_SMTP_USE_TLS).strip().lower()
    return value in {"1", "true", "yes", "on"}


def send_contact_email(contact: ContactEmail) -> None:
    host = _required_env(SMTP_HOST_ENV)
    username = _required_env(SMTP_USERNAME_ENV)
    password = _required_env(SMTP_PASSWORD_ENV)
    from_email = os.getenv(SMTP_FROM_EMAIL_ENV, username).strip() or username
    to_email = _required_env(CONTACT_TO_EMAIL_ENV)

    message = EmailMessage()
    message["Subject"] = f"{CONTACT_EMAIL_SUBJECT_PREFIX} {contact.name}"
    message["From"] = from_email
    message["To"] = to_email
    message["Reply-To"] = contact.email
    message.set_content(
        "\n".join(
            [
                CONTACT_EMAIL_HEADER,
                "",
                f"{CONTACT_EMAIL_SESSION_LABEL}: {contact.session_id}",
                "",
                f"Name: {contact.name}",
                f"Email: {contact.email}",
                "",
                "Content:",
                contact.content,
            ]
        )
    )

    try:
        with smtplib.SMTP(host, _smtp_port(), timeout=EMAIL_SEND_TIMEOUT_SECONDS) as smtp:
            if _smtp_use_tls():
                smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailServiceError(EMAIL_SEND_FAILURE_MESSAGE) from exc
