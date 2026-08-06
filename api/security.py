from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from jose import jwt
import secrets
import smtplib
import logging
import ssl
from email.message import EmailMessage

load_dotenv()

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
OTP_EXPIRE_MINUTES = 10

def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not configured")
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not configured")
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(hashed_password: str, plain_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except VerificationError:
        return False

def needs_rehash(hashed_password: str) -> bool:
    return ph.check_needs_rehash(hashed_password)


def generate_otp_code(length: int = 4) -> str:
    """Generate a numeric OTP code of given length (zero-padded)."""
    if length <= 0:
        length = 4
    max_val = 10 ** length
    return str(secrets.randbelow(max_val)).zfill(length)


def hash_otp(code: str) -> str:
    return ph.hash(str(code))


def verify_otp_hash(hashed: str, code: str) -> bool:
    try:
        return ph.verify(hashed, code)
    except (VerifyMismatchError, VerificationError):
        return False


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email using SMTP settings from environment. Returns True on success."""
    host = os.getenv("SMTP_HOST") or os.getenv("MAIL_HOST")
    port_raw = os.getenv("SMTP_PORT") or os.getenv("MAIL_PORT") or "0"
    user = os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME") or os.getenv("MAIL_USERNAME")
    password = os.getenv("SMTP_PASS") or os.getenv("SMTP_PASSWORD") or os.getenv("MAIL_PASSWORD")
    sender = os.getenv("SENDER_EMAIL") or os.getenv("SMTP_FROM") or os.getenv("FROM_EMAIL") or user

    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        return False

    if not host or not port or not sender:
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        return True
    except Exception:
        logger.exception("SMTP delivery failed for host=%s port=%s sender=%s", host, port, sender)
        return False
