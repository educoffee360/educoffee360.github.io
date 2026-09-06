from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List
from collections import Counter
import hashlib
import hmac
import os
import secrets

import schemas
import models
from database import get_db
from security import hash_password, verify_password, needs_rehash, create_access_token, decode_access_token
from email_service import EmailDeliveryError, send_email_otp, send_staff_emails

import json

from pywebpush import webpush, WebPushException

import logging
logger = logging.getLogger(__name__)

from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

router = APIRouter(prefix="/api")


class BatchUpdate(BaseModel):
    name: str
    year: str
    schedule: str
    fee_amount: int
    payment_cycle: str
    custom_period_start: datetime | None = None
    custom_period_end: datetime | None = None


def _looks_like_argon_hash(value: str) -> bool:
    return isinstance(value, str) and value.startswith("$argon2")


def _normalized_email(value: str) -> str:
    return str(value).strip().lower()


def _otp_digest(email: str, purpose: str, code: str) -> str:
    key = (os.getenv("OTP_SECRET") or os.getenv("SECRET_KEY") or "").encode("utf-8")
    if not key:
        raise HTTPException(503, "Email verification is temporarily unavailable")
    payload = f"{email}:{purpose}:{code}".encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None or payload.get("scope") in ("registration_email_verified", "password_reset_verified"):
            raise HTTPException(status_code=401, detail="Invalid Token")
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid Token")
        restriction = db.query(models.UserRestriction).filter(
            models.UserRestriction.user_id == user_id,
            models.UserRestriction.banned.is_(True),
        ).first()
        if restriction:
            raise HTTPException(status_code=403, detail="This account has been suspended")
        return {"user_id": user_id, "role": user.role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid Token")

def require_role(*allowed_roles):
    def checker(current_user = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return checker


def require_self_or_admin(user_id: str, current_user = Depends(get_current_user)):
    if current_user["role"] == "admin":
        return current_user
    if current_user["user_id"] != str(user_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user


def require_teacher_self_or_admin(teacher_id: str, current_user = Depends(get_current_user)):
    if current_user["role"] == "admin":
        return current_user
    if current_user["role"] != "teacher" or current_user["user_id"] != str(teacher_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user


def require_student_self_or_admin(student_id: str, current_user = Depends(get_current_user)):
    if current_user["role"] == "admin":
        return current_user
    if current_user["role"] != "student" or current_user["user_id"] != str(student_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user


def accessible_student_result_batches(student_id: str, db: Session, current_user):
    """Authorize result access and return the teacher's owned batch codes, if applicable."""
    role = current_user["role"]
    if role == "admin":
        return None
    if role == "student":
        if current_user["user_id"] != str(student_id):
            raise HTTPException(status_code=403, detail="Forbidden")
        return None
    if role != "teacher":
        raise HTTPException(status_code=403, detail="Forbidden")

    student = db.query(models.User).filter(
        models.User.id == student_id,
        models.User.role == "student",
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student Not Found")

    owned_batch_codes = {
        batch.code for batch in db.query(models.Batch).filter(
            models.Batch.teacher_id == current_user["user_id"]
        ).all()
    }
    if not owned_batch_codes.intersection(student.batch_codes or []):
        raise HTTPException(status_code=403, detail="Forbidden")
    return owned_batch_codes


def require_teacher_or_admin(current_user = Depends(get_current_user)):
    if current_user["role"] not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user


def require_student(current_user = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user


def require_batch_teacher_or_admin(batch_code: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    batch = db.query(models.Batch).filter(models.Batch.code == batch_code).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    if current_user["role"] == "admin":
        return current_user
    if current_user["role"] != "teacher" or current_user["user_id"] != batch.teacher_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user


def require_notice_owner_or_admin(notice_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    notice = db.query(models.Notice).filter(models.Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="Notice Not Found")
    if current_user["role"] == "admin":
        return current_user
    if current_user["role"] != "teacher" or current_user["user_id"] != notice.teacher_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user

@router.get("/users", response_model=List[schemas.UserResponse], status_code=200)
def get_all_users(db: Session = Depends(get_db), current_user = Depends(require_role("admin"))):
    return db.query(models.User).all()

class PushSubscriptionPayload(BaseModel):
    endpoint: str
    keys: dict


def _push_configured():
    return bool(
        os.getenv("VAPID_PUBLIC_KEY")
        and os.getenv("VAPID_PRIVATE_KEY")
        and os.getenv("VAPID_SUBJECT")
    )


def _send_push(subscription, payload):
    logger.info("PUSH: attempting delivery")
    if not _push_configured():
        return False

    try:
        logger.info("PUSH: calling webpush()")
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth,
                },
            },
            data=json.dumps(payload),
            vapid_private_key=os.getenv("VAPID_PRIVATE_KEY"),
            vapid_claims={
                "sub": os.getenv("VAPID_SUBJECT"),
            },
        )
        logger.info("PUSH: webpush() succeeded")
        return True

    except WebPushException as exc:
        status_code = getattr(
            getattr(exc, "response", None),
            "status_code",
            None,
        )

        # Subscription is no longer valid.
        if status_code in (404, 410):
            return "expired"

        logger.exception("Web push delivery failed")
        return False

    except Exception:
        logger.exception("Web push delivery failed")
        return False

@router.get("/user/{user_id}", response_model=schemas.UserResponse, status_code=200)
def get_user_by_id(user_id, db: Session = Depends(get_db), current_user = Depends(require_self_or_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User Not Found, make sure to register first")
    return user


@router.put("/user/{user_id}/profile", response_model=schemas.UserResponse, status_code=200)
def update_user_profile(user_id: str, payload: schemas.UserProfileUpdate, db: Session = Depends(get_db), current_user = Depends(require_self_or_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User Not Found")

    name = payload.name.strip()
    phone = payload.phone.strip()
    if not name or not phone:
        raise HTTPException(400, "Name and phone number are required")

    phone_owner = db.query(models.User).filter(
        models.User.phone == phone,
        models.User.id != user_id,
    ).first()
    if phone_owner:
        raise HTTPException(409, "This phone number is used by someone else.")

    user.name = name
    user.phone = phone
    if user.role == "teacher":
        user.center_name = (payload.center_name or "").strip() or None
    db.commit()
    db.refresh(user)
    return user


@router.post("/send_otp", status_code=200)
def send_otp(payload: schemas.OTPSendRequest, db: Session = Depends(get_db)):
    email = _normalized_email(payload.email)
    purpose = payload.purpose
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if purpose == "register" and existing_user:
        raise HTTPException(409, "An account with this email already exists")
    if purpose == "password_reset" and not existing_user:
        # Keep recovery responses neutral so this endpoint cannot enumerate accounts.
        return {"message": "If that account exists, a verification code was sent", "expires_in": 600, "resend_after": 60}

    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    latest = db.query(models.EmailOTP).filter(
        models.EmailOTP.email == email,
        models.EmailOTP.purpose == purpose,
    ).order_by(models.EmailOTP.created_at.desc()).first()
    if latest and latest.created_at > now - timedelta(seconds=60):
        retry_after = max(1, 60 - int((now - latest.created_at).total_seconds()))
        raise HTTPException(429, f"Please wait {retry_after} seconds before requesting another code")

    email_count = db.query(models.EmailOTP).filter(
        models.EmailOTP.email == email,
        models.EmailOTP.created_at >= hour_ago,
    ).count()
    global_count = db.query(models.EmailOTP).filter(
        models.EmailOTP.created_at >= hour_ago,
    ).count()
    if email_count >= 5:
        raise HTTPException(429, "Too many verification emails. Please try again later")
    if global_count >= 100:
        raise HTTPException(429, "Email verification is busy. Please try again later")

    code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = _otp_digest(email, purpose, code)
    try:
        send_email_otp(email, code, purpose)
    except EmailDeliveryError:
        raise HTTPException(503, "Unable to send verification email right now. Please try again later")

    db.add(models.EmailOTP(
        email=email,
        purpose=purpose,
        code_hash=code_hash,
        expires_at=now + timedelta(minutes=10),
    ))
    db.commit()
    return {"message": "Verification code sent", "expires_in": 600, "resend_after": 60}


@router.post("/verify_otp", status_code=200)
def verify_otp(payload: schemas.OTPVerifyRequest, db: Session = Depends(get_db)):
    email = _normalized_email(payload.email)
    now = datetime.utcnow()
    otp = db.query(models.EmailOTP).filter(
        models.EmailOTP.email == email,
        models.EmailOTP.purpose == payload.purpose,
        models.EmailOTP.consumed_at.is_(None),
    ).order_by(models.EmailOTP.created_at.desc()).first()
    if not otp:
        raise HTTPException(400, "Request a new verification code first")
    if otp.expires_at <= now:
        otp.consumed_at = now
        db.commit()
        raise HTTPException(400, "Verification code expired. Request a new one")
    if otp.attempts >= 5:
        otp.consumed_at = now
        db.commit()
        raise HTTPException(429, "Too many incorrect attempts. Request a new code")

    otp.attempts += 1
    expected = _otp_digest(email, payload.purpose, payload.code)
    if not hmac.compare_digest(otp.code_hash, expected):
        if otp.attempts >= 5:
            otp.consumed_at = now
        db.commit()
        raise HTTPException(400, "Incorrect verification code")

    otp.consumed_at = now
    db.commit()
    proof_scope = "password_reset_verified" if payload.purpose == "password_reset" else "registration_email_verified"
    verification_token = create_access_token({
        "sub": email,
        "scope": proof_scope,
        "otp_id": otp.id,
    }, expires_minutes=15)
    token_name = "reset_token" if payload.purpose == "password_reset" else "verification_token"
    return {"message": "Email verified", token_name: verification_token}


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
def register(user: schemas.User, db: Session = Depends(get_db)):
    email = _normalized_email(user.email)
    try:
        verification = decode_access_token(user.verification_token)
    except JWTError:
        raise HTTPException(403, "Email verification is invalid or expired")
    if (
        verification.get("scope") != "registration_email_verified"
        or _normalized_email(verification.get("sub", "")) != email
    ):
        raise HTTPException(403, "Verify this email before creating the account")

    if user.role in ("admin", "moderator"):
        raise HTTPException(403, "Staff accounts cannot be created through public registration")
    existing = db.query(models.User).filter(models.User.email == email).first()
    phone_in_use = db.query(models.User).filter(models.User.phone == user.phone).first()

    if existing:
        raise HTTPException(400, "Email already in use")

    if phone_in_use:
        raise HTTPException(400, "This phone number is used by someone else.")

    student_batch_codes = None
    if user.role == "student":
        submitted_codes = [str(code).strip().upper() for code in (user.batch_codes or []) if str(code).strip()]
        submitted_codes = list(dict.fromkeys(submitted_codes))
        if not submitted_codes:
            raise HTTPException(400, "A valid batch code is required for student registration")
        existing_codes = {
            batch.code for batch in db.query(models.Batch).filter(models.Batch.code.in_(submitted_codes)).all()
        }
        missing_codes = [code for code in submitted_codes if code not in existing_codes]
        if missing_codes:
            raise HTTPException(404, "Batch not found. Check the batch code with your teacher")
        student_batch_codes = submitted_codes

    new_user = models.User(
        name=user.name,
        phone=user.phone,
        email=email,
        password=hash_password(user.password),
        role=user.role,
        batch_codes=student_batch_codes,
        center_name=user.center_name if user.role == "teacher" else None,
        plan="Starter" if user.role == "teacher" else None,
    )

    db.add(new_user)
    db.flush()
    location = (user.location or "").strip() or None
    grade = (user.grade or "").strip() or None
    if location or grade:
        db.add(models.UserDemographic(user_id=new_user.id, location=location, grade=grade))
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/password/change", status_code=200)
def change_password(payload: schemas.PasswordChange, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(404, "User Not Found")
    if not verify_password(user.password, payload.current_password):
        raise HTTPException(400, "Current password is incorrect")
    if verify_password(user.password, payload.new_password):
        raise HTTPException(400, "New password must be different from your current password")
    user.password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/password/reset", status_code=200)
def reset_password(payload: schemas.PasswordReset, db: Session = Depends(get_db)):
    try:
        proof = decode_access_token(payload.reset_token)
    except JWTError:
        raise HTTPException(403, "Password reset verification is invalid or expired")
    if proof.get("scope") != "password_reset_verified":
        raise HTTPException(403, "Verify your email before resetting the password")

    email = _normalized_email(proof.get("sub", ""))
    otp_id = proof.get("otp_id")
    otp = db.query(models.EmailOTP).filter(
        models.EmailOTP.id == otp_id,
        models.EmailOTP.email == email,
        models.EmailOTP.purpose == "password_reset",
        models.EmailOTP.consumed_at.is_not(None),
    ).first()
    if not otp:
        raise HTTPException(403, "This password reset link has already been used or is invalid")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(403, "Password reset verification is invalid")
    user.password = hash_password(payload.new_password)
    otp.purpose = "password_reset_used"
    db.commit()
    return {"message": "Password reset successfully"}


@router.post("/login", status_code=200)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == _normalized_email(user.email)).first()

    if not db_user:
        raise HTTPException(404, "User doesn't exist")

    restriction = db.query(models.UserRestriction).filter(
        models.UserRestriction.user_id == db_user.id,
        models.UserRestriction.banned.is_(True),
    ).first()
    if restriction:
        raise HTTPException(403, "This account has been suspended")

    try:
        if verify_password(db_user.password, user.password):
            pass
        elif not _looks_like_argon_hash(db_user.password) and db_user.password == user.password:
            db_user.password = hash_password(user.password)
            db.commit()
            db.refresh(db_user)
        else:
            raise HTTPException(401, "Incorrect password")

        if _looks_like_argon_hash(db_user.password) and needs_rehash(db_user.password):
            db_user.password = hash_password(user.password)
            db.commit()
            db.refresh(db_user)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Incorrect password")

    token_data = {
        "sub": str(db_user.id),
        "role": db_user.role,
        "name": db_user.name
    }

    access_token = create_access_token(token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": db_user.role,
        "id": db_user.id,
    }



def _payment_period(batch: models.Batch, now: datetime | None = None):
    """Return the billing period that should currently be active for a batch."""
    now = now or datetime.utcnow()

    if batch.payment_cycle == "custom":
        if not batch.fee_period_start or not batch.fee_period_end:
            return None
        if batch.fee_period_end < now:
            return None
        return batch.fee_period_start, batch.fee_period_end

    if batch.payment_cycle == "monthly":
        period_start = datetime(now.year, now.month, 1)
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1)
        else:
            period_end = datetime(now.year, now.month + 1, 1)
        return period_start, period_end

    # six-months: January-June or July-December.
    if now.month <= 6:
        return datetime(now.year, 1, 1), datetime(now.year, 7, 1)
    return datetime(now.year, 7, 1), datetime(now.year + 1, 1, 1)


def _get_or_create_current_payment(student_id: str, batch: models.Batch, db: Session):
    """Create the current payment record if one does not already exist."""
    period = _payment_period(batch)
    if period is None:
        return None

    period_start, period_end = period
    payment = db.query(models.Payment).filter(
        models.Payment.student_id == student_id,
        models.Payment.batch_code == batch.code,
        models.Payment.period_start == period_start,
        models.Payment.period_end == period_end,
    ).first()

    if payment:
        if payment.status == "unpaid" and period_end < datetime.utcnow():
            payment.status = "overdue"
        return payment

    payment = models.Payment(
        student_id=student_id,
        batch_code=batch.code,
        amount=batch.fee_amount,
        period_start=period_start,
        period_end=period_end,
        status="unpaid",
    )
    db.add(payment)
    return payment


def _sync_batch_payments(batch: models.Batch, db: Session):
    """Ensure current payment records exist for all students enrolled in this batch."""
    students = db.query(models.User).filter(models.User.role == "student").all()
    for student in students:
        if batch.code in (student.batch_codes or []):
            _get_or_create_current_payment(student.id, batch, db)
    db.commit()


@router.get("/batches", response_model=List[schemas.Batch], status_code=200)
def get_all_batches(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user["role"] == "admin":
        return db.query(models.Batch).all()
    if current_user["role"] == "teacher":
        return db.query(models.Batch).filter(models.Batch.teacher_id == current_user["user_id"]).all()
    if current_user["role"] == "student":
        student = db.query(models.User).filter(models.User.id == current_user["user_id"]).first()
        return db.query(models.Batch).filter(models.Batch.code.in_(student.batch_codes or [])).all()
    raise HTTPException(403, "Moderators cannot inspect batches")


@router.get("/batch/validate/{batch_code}", status_code=200)
def validate_batch_code(batch_code: str, db: Session = Depends(get_db)):
    normalized_code = batch_code.strip().upper()
    batch = db.query(models.Batch).filter(models.Batch.code == normalized_code).first()
    if not batch:
        raise HTTPException(404, "Batch not found. Check the batch code with your teacher")
    return {"valid": True, "code": batch.code, "name": batch.name}


@router.post("/new_batch/", response_model=schemas.Batch, status_code=201)
def create_new_batch(batch: schemas.Batch, db: Session = Depends(get_db), current_user = Depends(require_role("teacher", "admin"))):
    if current_user["role"] == "teacher":
        teacher_id = current_user["user_id"]
    else:
        teacher_id = batch.teacher_id

    db_teacher = db.query(models.User).filter(models.User.id == teacher_id).first()
    if not db_teacher:
        raise HTTPException(404, "Teacher Not Found")
    if db_teacher.role != "teacher":
        raise HTTPException(403, "Students are not allowed to create batches")

    if batch.payment_cycle == "custom":
        if not batch.custom_period_start or not batch.custom_period_end:
            raise HTTPException(400, "Custom payment cycles require a start and end date")
        if batch.custom_period_start >= batch.custom_period_end:
            raise HTTPException(400, "Custom payment period must end after it starts")
    elif batch.custom_period_start or batch.custom_period_end:
        raise HTTPException(400, "Custom payment dates are only allowed for custom cycles")

    new_batch = models.Batch(
        code=batch.code.strip().upper(),
        name=batch.name,
        year=batch.year,
        schedule=batch.schedule,
        teacher_id=teacher_id,
        fee_amount=batch.fee_amount,
        payment_cycle=batch.payment_cycle,
        fee_period_start=batch.custom_period_start,
        fee_period_end=batch.custom_period_end,
    )

    db.add(new_batch)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Batch code already exists")
    db.refresh(new_batch)
    return new_batch


@router.put("/batch/{batch_code}", response_model=schemas.Batch)
def update_batch(batch_code: str, payload: BatchUpdate, db: Session = Depends(get_db), current_user = Depends(require_batch_teacher_or_admin)):
    batch = db.query(models.Batch).filter(models.Batch.code == batch_code).first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    if payload.fee_amount < 0:
        raise HTTPException(400, "Fee amount cannot be negative")

    if payload.payment_cycle not in ("monthly", "six-months", "custom"):
        raise HTTPException(400, "Invalid payment cycle")

    if payload.payment_cycle == "custom":
        if not payload.custom_period_start or not payload.custom_period_end:
            raise HTTPException(400, "Custom payment cycles require a start and end date")
        if payload.custom_period_start >= payload.custom_period_end:
            raise HTTPException(400, "Custom payment period must end after it starts")
    elif payload.custom_period_start or payload.custom_period_end:
        raise HTTPException(400, "Custom payment dates are only allowed for custom cycles")

    batch.name = payload.name
    batch.year = payload.year
    batch.schedule = payload.schedule
    batch.fee_amount = payload.fee_amount
    batch.payment_cycle = payload.payment_cycle
    batch.fee_period_start = payload.custom_period_start
    batch.fee_period_end = payload.custom_period_end

    db.commit()
    db.refresh(batch)
    return batch


@router.delete("/batch/{batch_code}", status_code=204)
def delete_batch(batch_code: str, db: Session = Depends(get_db), current_user = Depends(require_batch_teacher_or_admin)):
    batch = db.query(models.Batch).filter(models.Batch.code == batch_code).first()
    result_ids = [row.id for row in db.query(models.Result.id).filter(models.Result.batch_code == batch_code).all()]
    if result_ids:
        db.query(models.StudentScore).filter(models.StudentScore.result_id.in_(result_ids)).delete(synchronize_session=False)
        db.query(models.Result).filter(models.Result.id.in_(result_ids)).delete(synchronize_session=False)
    for student in db.query(models.User).filter(models.User.role == "student").all():
        if student.batch_codes and batch_code in student.batch_codes:
            student.batch_codes = [code for code in student.batch_codes if code != batch_code]
    db.delete(batch)
    db.commit()
    return None


@router.get(
    "/batches/{teacher_id}", response_model=List[schemas.Batch], status_code=200
)
def get_batches_by_teacher_id(teacher_id, db: Session = Depends(get_db), current_user = Depends(require_teacher_self_or_admin)):
    batches = db.query(models.Batch).filter(models.Batch.teacher_id == teacher_id)
    return batches


@router.put(
    "/enroll/{batch_code}", response_model=schemas.UserResponse, status_code=200
)
def enroll_in_batch(batch_code, db: Session = Depends(get_db), current_user = Depends(require_student)):
    student = db.query(models.User).filter(models.User.id == current_user["user_id"]).first()
    if not student:
        raise HTTPException(404, "Student Not Found")
    if student.role != "student":
        raise HTTPException(
            403, "This is for students to enroll in batches that teachers created."
        )

    batch = db.query(models.Batch).filter(models.Batch.code == batch_code).first()
    if not batch:
        raise HTTPException(
            404,
            "Batch not found. Make sure that your teacher has created this batch or check the batch code again.",
        )

    if student.batch_codes:
        if batch_code in list(student.batch_codes):
            raise HTTPException(409, "You are probably already enrolled in this batch")

    updated_batch_codes = [] if not student.batch_codes else list(student.batch_codes)
    updated_batch_codes.append(batch_code)
    student.batch_codes = updated_batch_codes

    _get_or_create_current_payment(student.id, batch, db)
    db.commit()
    db.refresh(student)
    return student

@router.get('/students_in_batch/{batch_code}', response_model=List[schemas.UserResponse], status_code=200)
def get_students_in_batch(batch_code, db: Session = Depends(get_db), current_user = Depends(require_batch_teacher_or_admin)):
    batch = db.query(models.Batch).filter(models.Batch.code == batch_code).first()
    if not batch:
        raise HTTPException(404, 'Batch not found')
    
    students = db.query(models.User).filter(models.User.role == 'student').all()
    students_in_batch = []
    for student in students:
        if batch_code in (student.batch_codes or []):
            students_in_batch.append(student)

    return students_in_batch

@router.get('/my_students/{teacher_id}', response_model=List[schemas.UserResponse], status_code=200)
def get_my_students(teacher_id, db: Session = Depends(get_db), current_user = Depends(require_teacher_self_or_admin)):
    my_batches = db.query(models.Batch).filter(models.Batch.teacher_id == teacher_id)
    my_batches_codes = []
    for batch in my_batches:
        my_batches_codes.append(batch.code)

    students = db.query(models.User).filter(models.User.role == 'student').all()
    my_students = []
    for student in students:
        for bc in (student.batch_codes or []):
            if bc in my_batches_codes:
                my_students.append(student)
                break
    
    return my_students


@router.delete('/my_students/{student_id}', response_model=schemas.UserResponse, status_code=200)
def remove_my_student(student_id: str, db: Session = Depends(get_db), current_user = Depends(require_teacher_or_admin)):
    student = db.query(models.User).filter(
        models.User.id == student_id,
        models.User.role == "student",
    ).first()
    if not student:
        raise HTTPException(404, "Student Not Found")

    if current_user["role"] == "admin":
        removable_codes = set(student.batch_codes or [])
    else:
        removable_codes = {
            batch.code for batch in db.query(models.Batch).filter(
                models.Batch.teacher_id == current_user["user_id"]
            ).all()
        }

    enrolled_codes = list(student.batch_codes or [])
    if not removable_codes.intersection(enrolled_codes):
        raise HTTPException(403, "This student is not enrolled in any of your batches")

    student.batch_codes = [code for code in enrolled_codes if code not in removable_codes]
    db.commit()
    db.refresh(student)
    return student

@router.get("/results", response_model=List[schemas.Result], status_code=200)
def get_all_results(db: Session = Depends(get_db), current_user = Depends(require_role("teacher", "admin"))):
    return db.query(models.Result).all()

@router.post('/new_result', status_code=201)
def create_result(result: schemas.Result, db: Session = Depends(get_db), current_user = Depends(require_teacher_or_admin)):
    batch = db.query(models.Batch).filter(models.Batch.code == result.batch_code).first()
    if not batch:
        raise HTTPException(404, 'Batch not found')
    if current_user["role"] == "teacher" and batch.teacher_id != current_user["user_id"]:
        raise HTTPException(403, "Forbidden")

    enrolled_ids = {
        student.id for student in db.query(models.User).filter(models.User.role == "student").all()
        if result.batch_code in (student.batch_codes or [])
    }
    score_ids = [score.student_id for score in result.scores]
    if len(score_ids) != len(set(score_ids)):
        raise HTTPException(400, "Duplicate student scores")
    if any(student_id not in enrolled_ids for student_id in score_ids):
        raise HTTPException(400, "A score contains a student who is not enrolled in this batch")

    new_result = models.Result(
        title=result.title,
        description=result.description,
        total_marks=result.total_marks,
        batch_code=result.batch_code
    )
    db.add(new_result)
    db.flush()

    for score in result.scores:
        db.add(models.StudentScore(
            result_id=new_result.id,
            student_id=score.student_id,
            marks=score.marks,
            remarks=score.remarks,
            absent=score.absent,
            seen_by_guardian=score.seen_by_guardian
        ))

    db.commit()
    return {'message': 'Results published successfully'}


@router.get('/results/batch/{batch_code}', status_code=200)
def get_results_by_batch(batch_code: str, db: Session = Depends(get_db), current_user = Depends(require_batch_teacher_or_admin)):
    results = db.query(models.Result).filter(models.Result.batch_code == batch_code).all()
    return [{
        "id": result.id,
        "title": result.title,
        "description": result.description,
        "total_marks": result.total_marks,
        "batch_code": result.batch_code,
        "scores": [{
            "student_id": score.student_id,
            "marks": score.marks,
            "remarks": score.remarks,
            "absent": score.absent,
            "seen_by_guardian": score.seen_by_guardian,
        } for score in result.scores],
    } for result in results]


@router.delete('/result/{result_id}', status_code=204)
def delete_result(result_id: str, db: Session = Depends(get_db), current_user = Depends(require_teacher_or_admin)):
    result = db.query(models.Result).filter(models.Result.id == result_id).first()
    if not result:
        raise HTTPException(404, "Result not found")
    batch = db.query(models.Batch).filter(models.Batch.code == result.batch_code).first()
    if current_user["role"] == "teacher" and (not batch or batch.teacher_id != current_user["user_id"]):
        raise HTTPException(403, "Forbidden")
    db.query(models.StudentScore).filter(models.StudentScore.result_id == result_id).delete()
    db.delete(result)
    db.commit()
    return None

@router.get('/results/student/{student_id}/{result_id}', status_code=200)
def get_student_result(student_id: str, result_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    accessible_batches = accessible_student_result_batches(student_id, db, current_user)
    if current_user["role"] == "student":
        student_id = current_user["user_id"]
    score = db.query(models.StudentScore).filter(
        models.StudentScore.student_id == student_id,
        models.StudentScore.result_id == result_id
    ).first()
    if not score:
        raise HTTPException(404, 'Result not found')
    
    parent = db.query(models.Result).filter(
        models.Result.id == score.result_id
    ).first()
    if accessible_batches is not None and (not parent or parent.batch_code not in accessible_batches):
        raise HTTPException(403, 'Forbidden')
    
    return {
        "result_id":        score.result_id,
        "marks":            score.marks,
        "remarks":          score.remarks,
        "absent":           score.absent,
        "seen_by_guardian": score.seen_by_guardian,
        "title":            parent.title if parent else "Untitled",
        "description":      parent.description if parent else "",
        "total_marks":      parent.total_marks if parent else None,
        "batch_code":       parent.batch_code if parent else None,
    }

@router.get('/results/student/{student_id}', status_code=200)
def get_student_results(student_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    accessible_batches = accessible_student_result_batches(student_id, db, current_user)
    if current_user["role"] == "student":
        student_id = current_user["user_id"]
    scores = db.query(models.StudentScore).filter(
        models.StudentScore.student_id == student_id
    ).all()
    if not scores:
        return []
    
    result = []
    for score in scores:
        parent = db.query(models.Result).filter(
            models.Result.id == score.result_id
        ).first()
        if accessible_batches is not None and (not parent or parent.batch_code not in accessible_batches):
            continue
        result.append({
            "result_id":        score.result_id,
            "marks":            score.marks,
            "remarks":          score.remarks,
            "absent":           score.absent,
            "seen_by_guardian": score.seen_by_guardian,
            "title":            parent.title if parent else "Untitled",
            "description":      parent.description if parent else "",
            "total_marks":      parent.total_marks if parent else None,
            "batch_code":       parent.batch_code if parent else None,
        })
    return result

@router.get("/notices", response_model=List[schemas.Notice], status_code=200)
def get_all_notices(db: Session = Depends(get_db), current_user = Depends(require_role("teacher", "admin"))):
    return db.query(models.Notice).all()


@router.get(
    "/notices/{student_id}", response_model=List[schemas.Notice], status_code=200
)
def get_notices_for_student(student_id, db: Session = Depends(get_db), current_user = Depends(require_student_self_or_admin)):
    if current_user["role"] == "student":
        student_id = current_user["user_id"]
    student = db.query(models.User).filter(models.User.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student Not Found")

    if not student.batch_codes or len(student.batch_codes) == 0:
        return []

    notices = db.query(models.Notice).all()
    filtered_notices = []
    for notice in notices:
        if any(batch_code in (notice.batch_codes or []) for batch_code in student.batch_codes):
            filtered_notices.append(notice)
    return filtered_notices


@router.post("/new_notice", response_model=schemas.Notice, status_code=201)
def create_new_notice(
    notice: schemas.Notice,
    db: Session = Depends(get_db),
    current_user=Depends(require_teacher_or_admin)
):
    teacher_id = (
        notice.teacher_id
        if current_user["role"] == "admin"
        else current_user["user_id"]
    )

    owned_codes = {
        b.code
        for b in db.query(models.Batch)
        .filter(models.Batch.teacher_id == teacher_id)
        .all()
    }

    if current_user["role"] != "admin" and any(
        code not in owned_codes for code in notice.batch_codes
    ):
        raise HTTPException(
            403,
            "Cannot publish to a batch you do not own"
        )

    new_notice = models.Notice(
        text=notice.text,
        teacher_id=teacher_id,
        batch_codes=notice.batch_codes,
        created_at=notice.created_at or datetime.utcnow(),
    )

    db.add(new_notice)
    db.commit()
    db.refresh(new_notice)

    # ---------------- PUSH NOTIFICATION DEBUG ----------------

    students = db.query(models.User).filter(
        models.User.role == "student"
    ).all()

    target_batches = set(notice.batch_codes or [])
    expired_subscriptions = []

    logger.info("PUSH DEBUG: target_batches=%s", target_batches)
    logger.info("PUSH DEBUG: total students=%d", len(students))

    for student in students:
        student_batches = set(student.batch_codes or [])

        logger.info(
            "PUSH DEBUG: student batches=%s",
            student.batch_codes
        )

        if not target_batches.intersection(student_batches):
            logger.info(
                "PUSH DEBUG: batch mismatch, skipping student"
            )
            continue

        logger.info("PUSH DEBUG: MATCHING STUDENT FOUND")

        subscriptions = db.query(models.PushSubscription).filter(
            models.PushSubscription.user_id == student.id
        ).all()

        logger.info(
            "PUSH DEBUG: matching student has %d subscriptions",
            len(subscriptions)
        )

        for subscription in subscriptions:
            logger.info("PUSH: attempting delivery")

            result = _send_push(
                subscription,
                {
                    "title": "New notice from EduCoffee",
                    "body": new_notice.text[:180],
                    "url": "/student-notices.html",
                    "tag": f"notice-{new_notice.id}",
                },
            )

            if result == "expired":
                expired_subscriptions.append(subscription)

    # Remove expired subscriptions
    for subscription in expired_subscriptions:
        db.delete(subscription)

    db.commit()

    return new_notice

@router.put("/notice/{notice_id}", response_model=schemas.Notice, status_code=200)
def update_notice(notice_id: str, notice: schemas.Notice, db: Session = Depends(get_db), current_user = Depends(require_notice_owner_or_admin)):
    db_notice = db.query(models.Notice).filter(models.Notice.id == notice_id).first()
    if not db_notice:
        raise HTTPException(404, "Notice Not Found")

    db_notice.text = notice.text
    if current_user["role"] == "admin":
        db_notice.teacher_id = notice.teacher_id
    elif any(code not in {b.code for b in db.query(models.Batch).filter(models.Batch.teacher_id == current_user["user_id"]).all()} for code in notice.batch_codes):
        raise HTTPException(403, "Cannot publish to a batch you do not own")
    db_notice.batch_codes = notice.batch_codes
    db_notice.created_at = notice.created_at or db_notice.created_at

    db.commit()
    db.refresh(db_notice)
    return db_notice

@router.delete("/notice/{notice_id}", status_code=204)
def delete_notice(notice_id: str, db: Session = Depends(get_db), current_user = Depends(require_notice_owner_or_admin)):
    db_notice = db.query(models.Notice).filter(models.Notice.id == notice_id).first()
    if not db_notice:
        raise HTTPException(404, "Notice Not Found")

    db.delete(db_notice)
    db.commit()
    return None

@router.get('/my_notices/{teacher_id}', response_model=List[schemas.Notice], status_code=200)
def get_my_notices(teacher_id, db: Session = Depends(get_db), current_user = Depends(require_teacher_self_or_admin)):
    teacher = db.query(models.User).filter(models.User.id == teacher_id).first()
    if not teacher:
        raise HTTPException(404, "Teacher Not Found")

    if teacher.role != 'teacher':
        raise HTTPException(403, 'Not for students.')

    notices = db.query(models.Notice).filter(models.Notice.teacher_id == teacher_id).all()
    
    return notices

@router.get("/push/public-key")
def get_push_public_key(
    current_user = Depends(require_student),
):
    public_key = os.getenv("VAPID_PUBLIC_KEY")

    if not public_key:
        raise HTTPException(
            503,
            "Push notifications are not configured yet."
        )

    return {"public_key": public_key}


@router.post("/push/subscribe")
def subscribe_to_push(
    payload: PushSubscriptionPayload,
    db: Session = Depends(get_db),
    current_user = Depends(require_student),
):
    endpoint = payload.endpoint.strip()
    keys = payload.keys or {}

    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        raise HTTPException(400, "Invalid push subscription")

    existing = db.query(models.PushSubscription).filter(
        models.PushSubscription.endpoint == endpoint
    ).first()

    if existing:
        existing.user_id = current_user["user_id"]
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        db.add(models.PushSubscription(
            user_id=current_user["user_id"],
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        ))

    db.commit()

    return {"message": "Push notifications enabled"}


@router.delete("/push/subscribe")
def unsubscribe_from_push(
    payload: PushSubscriptionPayload,
    db: Session = Depends(get_db),
    current_user = Depends(require_student),
):
    subscription = db.query(models.PushSubscription).filter(
        models.PushSubscription.user_id == current_user["user_id"],
        models.PushSubscription.endpoint == payload.endpoint,
    ).first()

    if subscription:
        db.delete(subscription)
        db.commit()

    return {"message": "Push notifications disabled"}

def _parent_message_response(message, teacher_name: str):
    return {
        "id": message.id,
        "teacher_id": message.teacher_id,
        "teacher_name": teacher_name,
        "student_id": message.student_id,
        "subject": message.subject,
        "body": message.body,
        "batch_codes": message.batch_codes or [],
        "created_at": message.created_at,
    }


@router.post('/messages', response_model=schemas.ParentMessageResponse, status_code=201)
def send_parent_message(payload: schemas.ParentMessageCreate, db: Session = Depends(get_db), current_user = Depends(require_role("teacher"))):
    teacher = db.query(models.User).filter(models.User.id == current_user["user_id"]).first()
    student = db.query(models.User).filter(
        models.User.id == payload.student_id,
        models.User.role == "student",
    ).first()
    if not teacher or not student:
        raise HTTPException(404, "Teacher or student not found")

    owned_codes = {
        batch.code for batch in db.query(models.Batch).filter(
            models.Batch.teacher_id == teacher.id
        ).all()
    }
    shared_codes = sorted(owned_codes.intersection(student.batch_codes or []))
    if not shared_codes:
        raise HTTPException(403, "This student is not enrolled in any of your batches")

    subject = payload.subject.strip()
    body = payload.body.strip()
    if not subject or not body:
        raise HTTPException(400, "Subject and message are required")

    message = models.ParentMessage(
        teacher_id=teacher.id,
        student_id=student.id,
        subject=subject,
        body=body,
        batch_codes=shared_codes,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return _parent_message_response(message, teacher.name)


@router.post('/messages/broadcast', status_code=201)
def broadcast_parent_message(payload: schemas.ParentBroadcastCreate, db: Session = Depends(get_db), current_user = Depends(require_role("teacher"))):
    teacher = db.query(models.User).filter(models.User.id == current_user["user_id"]).first()
    if not teacher:
        raise HTTPException(404, "Teacher Not Found")

    owned_codes = {
        batch.code for batch in db.query(models.Batch).filter(
            models.Batch.teacher_id == teacher.id
        ).all()
    }
    target_codes = set(payload.batch_codes) if payload.batch_codes else owned_codes
    if not target_codes:
        raise HTTPException(400, "Create a batch before sending a broadcast")
    if not target_codes.issubset(owned_codes):
        raise HTTPException(403, "Cannot broadcast to a batch you do not own")

    subject = payload.subject.strip()
    body = payload.body.strip()
    if not subject or not body:
        raise HTTPException(400, "Subject and message are required")

    recipients = []
    for student in db.query(models.User).filter(models.User.role == "student").all():
        matching_codes = sorted(target_codes.intersection(student.batch_codes or []))
        if matching_codes:
            recipients.append((student, matching_codes))

    for student, matching_codes in recipients:
        db.add(models.ParentMessage(
            teacher_id=teacher.id,
            student_id=student.id,
            subject=subject,
            body=body,
            batch_codes=matching_codes,
        ))
    db.commit()
    return {"message": "Broadcast sent", "recipient_count": len(recipients)}


@router.get('/messages/student/{student_id}', response_model=List[schemas.ParentMessageResponse], status_code=200)
def get_parent_messages(student_id: str, db: Session = Depends(get_db), current_user = Depends(require_student_self_or_admin)):
    if current_user["role"] == "student":
        student_id = current_user["user_id"]
    student = db.query(models.User).filter(
        models.User.id == student_id,
        models.User.role == "student",
    ).first()
    if not student:
        raise HTTPException(404, "Student Not Found")

    messages = db.query(models.ParentMessage).filter(
        models.ParentMessage.student_id == student_id
    ).order_by(models.ParentMessage.created_at.desc()).all()
    teacher_ids = {message.teacher_id for message in messages}
    teacher_names = {
        teacher.id: teacher.name for teacher in db.query(models.User).filter(
            models.User.id.in_(teacher_ids)
        ).all()
    } if teacher_ids else {}
    return [
        _parent_message_response(message, teacher_names.get(message.teacher_id, "Teacher"))
        for message in messages
    ]


# --- Staff operations ------------------------------------------------------

def _staff_user_response(user, demographics, restrictions, include_phone=False):
    demographic = demographics.get(user.id)
    restriction = restrictions.get(user.id)
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "phone": user.phone if include_phone else None,
        "role": user.role, "plan": user.plan, "center_name": user.center_name,
        "location": demographic.location if demographic else None,
        "grade": demographic.grade if demographic else None,
        "banned": bool(restriction and restriction.banned),
        "ban_reason": restriction.reason if restriction and restriction.banned else None,
    }


@router.get("/staff/users", status_code=200)
def staff_users(db: Session = Depends(get_db), current_user = Depends(require_role("admin", "moderator"))):
    users = db.query(models.User).order_by(models.User.name.asc()).all()
    demographics = {row.user_id: row for row in db.query(models.UserDemographic).all()}
    restrictions = {row.user_id: row for row in db.query(models.UserRestriction).all()}
    return [_staff_user_response(user, demographics, restrictions, current_user["role"] == "admin") for user in users]


@router.get("/staff/analytics", status_code=200)
def staff_analytics(db: Session = Depends(get_db), current_user = Depends(require_role("admin", "moderator"))):
    users = db.query(models.User).all()
    demographics = db.query(models.UserDemographic).all()
    locations = Counter(row.location for row in demographics if row.location)
    grades = Counter(row.grade for row in demographics if row.grade)
    plans = Counter((user.plan or "None") for user in users if user.role == "teacher")
    roles = Counter(user.role for user in users)
    return {
        "total_users": len(users), "roles": dict(roles), "plans": dict(plans),
        "locations": [{"label": label, "count": count} for label, count in locations.most_common(12)],
        "grades": [{"label": label, "count": count} for label, count in grades.most_common(12)],
        "profiled_users": len({row.user_id for row in demographics if row.location or row.grade}),
    }


@router.get("/billing/config", status_code=200)
def billing_config(current_user = Depends(require_role("teacher", "admin"))):
    return {
        "provider": "Nagad", "payment_number": os.getenv("NAGAD_PAYMENT_NUMBER", "").strip(),
        "review_window": "within 24 hours",
        "plans": {"Professional": {"amount": 150, "period": "1 month"}, "Elite": {"amount": 600, "period": "6 months"}},
    }


def _upgrade_response(request, db):
    teacher = db.query(models.User).filter(models.User.id == request.teacher_id).first()
    reviewer = db.query(models.User).filter(models.User.id == request.reviewed_by).first() if request.reviewed_by else None
    return {
        "id": request.id, "teacher_id": request.teacher_id,
        "teacher_name": teacher.name if teacher else "Unknown teacher",
        "teacher_email": teacher.email if teacher else "", "current_plan": teacher.plan if teacher else None,
        "requested_plan": request.requested_plan, "method": request.method, "trx_id": request.trx_id,
        "payment_phone": request.payment_phone, "status": request.status, "review_note": request.review_note,
        "reviewed_by_name": reviewer.name if reviewer else None,
        "requested_at": request.requested_at, "reviewed_at": request.reviewed_at,
    }


@router.post("/upgrade-requests", status_code=201)
def create_upgrade_request(payload: schemas.PlanUpgradeCreate, db: Session = Depends(get_db), current_user = Depends(require_role("teacher"))):
    teacher = db.query(models.User).filter(models.User.id == current_user["user_id"]).first()
    if teacher.plan == payload.requested_plan:
        raise HTTPException(400, "This plan is already active")
    if db.query(models.PlanUpgradeRequest).filter(models.PlanUpgradeRequest.teacher_id == teacher.id, models.PlanUpgradeRequest.status == "pending").first():
        raise HTTPException(409, "You already have a pending upgrade request")
    trx_id = (payload.trx_id or "").strip().upper() or None
    payment_phone = (payload.payment_phone or "").strip() or None
    if payload.method == "nagad" and (not trx_id or not payment_phone):
        raise HTTPException(400, "Nagad TrxID and payment phone number are required")
    if trx_id and db.query(models.PlanUpgradeRequest).filter(models.PlanUpgradeRequest.trx_id == trx_id).first():
        raise HTTPException(409, "This TrxID has already been submitted")
    request = models.PlanUpgradeRequest(teacher_id=teacher.id, requested_plan=payload.requested_plan, method=payload.method, trx_id=trx_id, payment_phone=payment_phone)
    db.add(request); db.commit(); db.refresh(request)
    return _upgrade_response(request, db)


@router.get("/upgrade-requests/mine", status_code=200)
def my_upgrade_requests(db: Session = Depends(get_db), current_user = Depends(require_role("teacher"))):
    requests = db.query(models.PlanUpgradeRequest).filter(models.PlanUpgradeRequest.teacher_id == current_user["user_id"]).order_by(models.PlanUpgradeRequest.requested_at.desc()).all()
    return [_upgrade_response(request, db) for request in requests]


@router.get("/staff/upgrade-requests", status_code=200)
def staff_upgrade_requests(db: Session = Depends(get_db), current_user = Depends(require_role("admin"))):
    return [_upgrade_response(request, db) for request in db.query(models.PlanUpgradeRequest).order_by(models.PlanUpgradeRequest.requested_at.desc()).all()]


@router.post("/staff/upgrade-requests/{request_id}/decision", status_code=200)
def decide_upgrade_request(request_id: str, payload: schemas.StaffDecision, db: Session = Depends(get_db), current_user = Depends(require_role("admin"))):
    request = db.query(models.PlanUpgradeRequest).filter(models.PlanUpgradeRequest.id == request_id).first()
    if not request: raise HTTPException(404, "Upgrade request not found")
    if request.status != "pending": raise HTTPException(409, "This request has already been reviewed")
    teacher = db.query(models.User).filter(models.User.id == request.teacher_id, models.User.role == "teacher").first()
    if not teacher: raise HTTPException(404, "Teacher not found")
    request.status = "approved" if payload.approved else "rejected"
    request.review_note = (payload.note or "").strip() or None
    request.reviewed_by = current_user["user_id"]; request.reviewed_at = datetime.utcnow()
    if payload.approved: teacher.plan = request.requested_plan
    db.commit(); db.refresh(request)
    return _upgrade_response(request, db)


@router.put("/staff/teachers/{teacher_id}/plan", status_code=200)
def set_teacher_plan(teacher_id: str, payload: schemas.PlanSet, db: Session = Depends(get_db), current_user = Depends(require_role("admin"))):
    teacher = db.query(models.User).filter(models.User.id == teacher_id, models.User.role == "teacher").first()
    if not teacher: raise HTTPException(404, "Teacher not found")
    teacher.plan = payload.plan; db.commit()
    return {"message": "Teacher plan updated", "teacher_id": teacher.id, "plan": teacher.plan}


@router.post("/staff/teachers/{teacher_id}/ban", status_code=200)
def ban_teacher(teacher_id: str, payload: schemas.BanAction, db: Session = Depends(get_db), current_user = Depends(require_role("admin"))):
    teacher = db.query(models.User).filter(models.User.id == teacher_id, models.User.role == "teacher").first()
    if not teacher: raise HTTPException(404, "Teacher not found")
    restriction = db.query(models.UserRestriction).filter(models.UserRestriction.user_id == teacher_id).first()
    if not restriction:
        restriction = models.UserRestriction(user_id=teacher_id); db.add(restriction)
    restriction.banned = True; restriction.reason = payload.reason.strip()
    restriction.banned_by = current_user["user_id"]; restriction.banned_at = datetime.utcnow()
    db.commit()
    return {"message": "Teacher suspended"}


@router.delete("/staff/teachers/{teacher_id}/ban", status_code=200)
def unban_teacher(teacher_id: str, db: Session = Depends(get_db), current_user = Depends(require_role("admin"))):
    restriction = db.query(models.UserRestriction).filter(models.UserRestriction.user_id == teacher_id).first()
    if not restriction or not restriction.banned: raise HTTPException(404, "Teacher is not suspended")
    restriction.banned = False; restriction.reason = None; restriction.banned_by = None; restriction.banned_at = None
    db.commit()
    return {"message": "Teacher restored"}


def _ban_request_response(request, db):
    target = db.query(models.User).filter(models.User.id == request.target_user_id).first()
    requester = db.query(models.User).filter(models.User.id == request.requested_by).first()
    return {"id": request.id, "target_user_id": request.target_user_id, "target_name": target.name if target else "Unknown teacher", "target_email": target.email if target else "", "requested_by_name": requester.name if requester else "Unknown moderator", "reason": request.reason, "status": request.status, "review_note": request.review_note, "requested_at": request.requested_at}


@router.post("/staff/teachers/{teacher_id}/ban-requests", status_code=201)
def request_teacher_ban(teacher_id: str, payload: schemas.BanAction, db: Session = Depends(get_db), current_user = Depends(require_role("moderator"))):
    if not db.query(models.User).filter(models.User.id == teacher_id, models.User.role == "teacher").first(): raise HTTPException(404, "Teacher not found")
    if db.query(models.BanRequest).filter(models.BanRequest.target_user_id == teacher_id, models.BanRequest.status == "pending").first(): raise HTTPException(409, "A ban request is already pending for this teacher")
    request = models.BanRequest(target_user_id=teacher_id, requested_by=current_user["user_id"], reason=payload.reason.strip())
    db.add(request); db.commit(); db.refresh(request)
    return _ban_request_response(request, db)


@router.get("/staff/ban-requests", status_code=200)
def list_ban_requests(db: Session = Depends(get_db), current_user = Depends(require_role("admin", "moderator"))):
    query = db.query(models.BanRequest)
    if current_user["role"] == "moderator": query = query.filter(models.BanRequest.requested_by == current_user["user_id"])
    return [_ban_request_response(request, db) for request in query.order_by(models.BanRequest.requested_at.desc()).all()]


@router.post("/staff/ban-requests/{request_id}/decision", status_code=200)
def decide_ban_request(request_id: str, payload: schemas.StaffDecision, db: Session = Depends(get_db), current_user = Depends(require_role("admin"))):
    request = db.query(models.BanRequest).filter(models.BanRequest.id == request_id).first()
    if not request: raise HTTPException(404, "Ban request not found")
    if request.status != "pending": raise HTTPException(409, "This request has already been reviewed")
    request.status = "approved" if payload.approved else "rejected"; request.reviewed_by = current_user["user_id"]
    request.review_note = (payload.note or "").strip() or None; request.reviewed_at = datetime.utcnow()
    if payload.approved:
        restriction = db.query(models.UserRestriction).filter(models.UserRestriction.user_id == request.target_user_id).first()
        if not restriction: restriction = models.UserRestriction(user_id=request.target_user_id); db.add(restriction)
        restriction.banned = True; restriction.reason = request.reason
        restriction.banned_by = current_user["user_id"]; restriction.banned_at = datetime.utcnow()
    db.commit()
    return _ban_request_response(request, db)


@router.post("/staff/email", status_code=200)
def staff_send_email(payload: schemas.StaffEmailCreate, db: Session = Depends(get_db), current_user = Depends(require_role("admin", "moderator"))):
    recipient_ids = list(dict.fromkeys(payload.recipient_ids))
    users = db.query(models.User).filter(models.User.id.in_(recipient_ids)).all()
    if len(users) != len(recipient_ids): raise HTTPException(400, "One or more recipients no longer exist")
    recipients = [user.email for user in users]
    try: sent, failed = send_staff_emails(recipients, payload.subject.strip(), payload.body.strip())
    except EmailDeliveryError: raise HTTPException(503, "Email delivery is temporarily unavailable")
    db.add(models.EmailCampaign(sender_id=current_user["user_id"], subject=payload.subject.strip(), body=payload.body.strip(), recipient_count=len(recipients), sent_count=len(sent), failed_recipients=failed))
    db.commit()
    return {"message": f"Sent {len(sent)} of {len(recipients)} emails", "sent_count": len(sent), "failed": failed}


@router.post("/staff/moderators", status_code=201)
def create_moderator(payload: schemas.ModeratorCreate, db: Session = Depends(get_db), current_user = Depends(require_role("admin"))):
    email = _normalized_email(payload.email)
    if db.query(models.User).filter(models.User.email == email).first(): raise HTTPException(409, "Email already in use")
    if db.query(models.User).filter(models.User.phone == payload.phone.strip()).first(): raise HTTPException(409, "Phone number already in use")
    moderator = models.User(name=payload.name.strip(), email=email, phone=payload.phone.strip(), password=hash_password(payload.password), role="moderator", plan=None, batch_codes=None)
    db.add(moderator); db.commit(); db.refresh(moderator)
    return {"id": moderator.id, "name": moderator.name, "email": moderator.email, "role": moderator.role}


@router.get("/payments/teacher/{teacher_id}", response_model=List[schemas.Payment], status_code=200)
def get_teacher_payments(
    teacher_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_teacher_self_or_admin),
):
    batches = db.query(models.Batch).filter(models.Batch.teacher_id == teacher_id).all()
    batch_codes = [batch.code for batch in batches]
    if not batch_codes:
        return []

    students = db.query(models.User).filter(models.User.role == "student").all()
    payments = []

    for batch in batches:
        for student in students:
            if batch.code not in (student.batch_codes or []):
                continue
            payment = _get_or_create_current_payment(student.id, batch, db)
            if payment:
                payments.append(payment)

    db.commit()
    return payments


@router.put("/payment/{student_id}/{batch_code}", response_model=schemas.Payment, status_code=200)
def update_payment(
    student_id: str,
    batch_code: str,
    payload: schemas.PaymentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_teacher_or_admin),
):
    batch = db.query(models.Batch).filter(models.Batch.code == batch_code).first()
    if not batch:
        raise HTTPException(404, "Batch not found")

    if current_user["role"] != "admin" and batch.teacher_id != current_user["user_id"]:
        raise HTTPException(403, "You do not manage this batch")

    student = db.query(models.User).filter(
        models.User.id == student_id,
        models.User.role == "student",
    ).first()
    if not student or batch_code not in (student.batch_codes or []):
        raise HTTPException(404, "Student is not enrolled in this batch")

    payment = _get_or_create_current_payment(student_id, batch, db)
    if payment is None:
        raise HTTPException(400, "This custom payment period has expired. Set a new period on the batch first")

    payment.status = payload.status
    payment.paid_at = datetime.utcnow() if payload.status == "paid" else None

    db.commit()
    db.refresh(payment)
    return payment

