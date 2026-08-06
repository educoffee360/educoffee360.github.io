from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from jose import jwt
import secrets
import logging
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
    """Send an email through Brevo's HTTPS API. Returns True on acceptance."""
    api_key = os.getenv("BREVO_API_KEY")
    sender = os.getenv("BREVO_FROM_EMAIL")
    sender_name = os.getenv("BREVO_FROM_NAME", "EduCoffee")
    if not api_key or not sender:
        logger.error("Brevo is not configured: BREVO_API_KEY and BREVO_FROM_EMAIL are required")
        return False

    payload = json.dumps({
        "sender": {"name": sender_name, "email": sender},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body,
    }).encode("utf-8")
    request = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        method="POST",
        headers={
            "api-key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "EduCoffee/1.0",
        },
    )

    try:
        with urlopen(request, timeout=15) as response:
            return 200 <= response.status < 300
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error("Brevo rejected email with status %s: %s", exc.code, error_body)
        return False
    except (URLError, TimeoutError, OSError):
        logger.exception("Brevo API request failed")
        return False
