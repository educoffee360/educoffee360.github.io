import base64
import logging
import os
from html import escape
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.message import EmailMessage

import requests


logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    pass


def _required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise EmailDeliveryError(f"Missing required email setting: {name}")
    return value


def _gmail_access_token() -> str:
    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": _required_setting("GOOGLE_CLIENT_ID"),
                "client_secret": _required_setting("GOOGLE_CLIENT_SECRET"),
                "refresh_token": _required_setting("GOOGLE_REFRESH_TOKEN"),
                "grant_type": "refresh_token",
            },
            timeout=12,
        )
    except requests.RequestException as exc:
        raise EmailDeliveryError("Could not connect to Google OAuth") from exc

    if not response.ok:
        logger.error("Google OAuth token request failed with status %s", response.status_code)
        raise EmailDeliveryError("Google rejected the email authorization")
    try:
        token = response.json().get("access_token")
    except ValueError as exc:
        raise EmailDeliveryError("Google OAuth returned an invalid response") from exc
    if not token:
        raise EmailDeliveryError("Google OAuth response did not include an access token")
    return token


def send_email_otp(recipient: str, code: str, purpose: str = "register") -> None:
    sender = _required_setting("OTP_FROM_EMAIL")
    is_password_reset = purpose == "password_reset"
    action = "reset your password" if is_password_reset else "finish creating your account"
    subject_action = "password reset" if is_password_reset else "verification"
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = f"EduCoffee <{sender}>"
    message["Subject"] = f"{code} is your EduCoffee {subject_action} code"
    message.set_content(
        f"Your EduCoffee code is {code}. Use it to {action}. "
        "It expires in 10 minutes. If you did not request this, ignore this email."
    )
    message.add_alternative(
        f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:28px;color:#2d241e">
          <h1 style="color:#3e2723;margin:0 0 10px">EduCoffee</h1>
          <p style="color:#7d6e64">Use this code to {action}:</p>
          <div style="font-size:34px;font-weight:700;letter-spacing:8px;color:#3e2723;background:#fdfbf7;border:1px solid #eadfd6;border-radius:14px;padding:18px;text-align:center">{code}</div>
          <p style="color:#7d6e64;font-size:13px;margin-top:18px">This code expires in 10 minutes. Never share it with anyone.</p>
        </div>
        """,
        subtype="html",
    )
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")

    try:
        response = requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {_gmail_access_token()}",
                "Content-Type": "application/json",
            },
            json={"raw": raw},
            timeout=12,
        )
    except requests.RequestException as exc:
        raise EmailDeliveryError("Could not connect to Gmail") from exc

    if not response.ok:
        logger.error("Gmail send request failed with status %s", response.status_code)
        raise EmailDeliveryError("Gmail rejected the message")


def send_registration_otp(recipient: str, code: str) -> None:
    """Backward-compatible wrapper for existing imports/tests."""
    send_email_otp(recipient, code, "register")


def send_staff_email(recipient: str, subject: str, body: str, access_token: str = None) -> None:
    sender = _required_setting("OTP_FROM_EMAIL")
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = f"EduCoffee <{sender}>"
    message["Subject"] = subject
    message.set_content(body)
    safe_body = escape(body).replace("\n", "<br>")
    message.add_alternative(
        f'<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:28px;color:#2d241e">'
        f'<h1 style="color:#3e2723">EduCoffee</h1><div style="line-height:1.65">{safe_body}</div></div>',
        subtype="html",
    )
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    try:
        response = requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {access_token or _gmail_access_token()}",
                "Content-Type": "application/json",
            },
            json={"raw": raw},
            timeout=12,
        )
    except requests.RequestException as exc:
        raise EmailDeliveryError("Could not connect to Gmail") from exc
    if not response.ok:
        logger.error("Gmail staff email failed with status %s", response.status_code)
        raise EmailDeliveryError("Gmail rejected the message")


def send_staff_emails(recipients, subject: str, body: str):
    token = _gmail_access_token()
    sent = []
    failed = []

    def deliver(recipient):
        try:
            send_staff_email(recipient, subject, body, token)
            return recipient, True
        except EmailDeliveryError:
            return recipient, False

    with ThreadPoolExecutor(max_workers=min(5, max(1, len(recipients)))) as executor:
        futures = [executor.submit(deliver, recipient) for recipient in recipients]
        for future in as_completed(futures):
            recipient, delivered = future.result()
            (sent if delivered else failed).append(recipient)
    return sent, failed
