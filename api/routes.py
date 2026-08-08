from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List
import hashlib
import hmac
import os
import secrets

try:
    from . import schemas, models
    from .database import get_db
    from .security import hash_password, verify_password, needs_rehash, create_access_token, decode_access_token
    from .email_service import EmailDeliveryError, send_registration_otp
except ImportError:  # Support `uvicorn main:app` when launched inside api/.
    import schemas
    import models
    from database import get_db
    from security import hash_password, verify_password, needs_rehash, create_access_token, decode_access_token
    from email_service import EmailDeliveryError, send_registration_otp
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

router = APIRouter(prefix="/api")


class BatchUpdate(BaseModel):
    name: str
    year: str
    schedule: str


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

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        role = payload.get("role")
        if user_id is None or payload.get("scope") == "registration_email_verified":
            raise HTTPException(status_code=401, detail="Invalid Token")
        return {"user_id": user_id, "role": role}
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
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")

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
        send_registration_otp(email, code)
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
    verification_token = create_access_token({
        "sub": email,
        "scope": "registration_email_verified",
    }, expires_minutes=15)
    return {"message": "Email verified", "verification_token": verification_token}


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

    if user.role == "admin":
        raise HTTPException(403, "Admin accounts cannot be created through public registration")
    existing = db.query(models.User).filter(models.User.email == email).first()
    phone_in_use = db.query(models.User).filter(models.User.phone == user.phone).first()

    if existing:
        raise HTTPException(400, "Email already in use")

    if phone_in_use:
        raise HTTPException(400, "This phone number is used by someone else.")

    new_user = models.User(
        name=user.name,
        phone=user.phone,
        email=email,
        password=hash_password(user.password),
        role=user.role,
        batch_codes=user.batch_codes if user.role == "student" else None,
        center_name=user.center_name if user.role == "teacher" else None,
        plan=user.plan if user.role == "teacher" else None,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", status_code=200)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()

    if not db_user:
        raise HTTPException(404, "User doesn't exist")

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


@router.get("/batches", response_model=List[schemas.Batch], status_code=200)
def get_all_batches(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(models.Batch).all()


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

    new_batch = models.Batch(
        code=batch.code,
        name=batch.name,
        year=batch.year,
        schedule=batch.schedule,
        teacher_id=teacher_id,
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
    batch.name = payload.name
    batch.year = payload.year
    batch.schedule = payload.schedule
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
def create_new_notice(notice: schemas.Notice, db: Session = Depends(get_db), current_user = Depends(require_teacher_or_admin)):
    teacher_id = notice.teacher_id if current_user["role"] == "admin" else current_user["user_id"]
    owned_codes = {b.code for b in db.query(models.Batch).filter(models.Batch.teacher_id == teacher_id).all()}
    if current_user["role"] != "admin" and any(code not in owned_codes for code in notice.batch_codes):
        raise HTTPException(403, "Cannot publish to a batch you do not own")
    new_notice = models.Notice(
        text=notice.text,
        teacher_id=teacher_id,
        batch_codes=notice.batch_codes,
        created_at=notice.created_at or datetime.utcnow(),
    )

    db.add(new_notice)
    db.commit()
    db.refresh(new_notice)
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
