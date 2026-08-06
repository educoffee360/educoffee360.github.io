from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List

try:
    from . import schemas, models
    from .database import get_db
    from .security import hash_password, verify_password, needs_rehash, create_access_token, decode_access_token, generate_otp_code, hash_otp, verify_otp_hash, OTP_EXPIRE_MINUTES, send_email
except ImportError:  # Support `uvicorn main:app` when launched inside api/.
    import schemas
    import models
    from database import get_db
    from security import hash_password, verify_password, needs_rehash, create_access_token, decode_access_token, generate_otp_code, hash_otp, verify_otp_hash, OTP_EXPIRE_MINUTES, send_email
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

router = APIRouter(prefix="/api")


class OTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "register"


class OTPVerification(BaseModel):
    email: EmailStr
    purpose: str
    code: str = Field(min_length=4, max_length=10)
    new_password: str | None = Field(default=None, min_length=8)


class BatchUpdate(BaseModel):
    name: str
    year: str
    schedule: str


def _looks_like_argon_hash(value: str) -> bool:
    return isinstance(value, str) and value.startswith("$argon2")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        role = payload.get("role")
        if user_id is None:
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


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
def register(user: schemas.User, db: Session = Depends(get_db)):
    if user.role == "admin":
        raise HTTPException(403, "Admin accounts cannot be created through public registration")
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    phone_in_use = db.query(models.User).filter(models.User.phone == user.phone).first()

    if existing:
        raise HTTPException(400, "Email already in use")

    if phone_in_use:
        raise HTTPException(400, "This phone number is used by someone else.")

    new_user = models.User(
        name=user.name,
        phone=user.phone,
        email=user.email,
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


@router.post("/send_otp", status_code=200)
def send_otp(payload: OTPRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    purpose = payload.purpose

    if purpose == "reset" and not db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=404, detail="User not found")

    code = generate_otp_code()
    hashed = hash_otp(code)
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)

    db.query(models.OTP).filter(
        models.OTP.email == email,
        models.OTP.purpose == purpose,
    ).delete(synchronize_session=False)
    new_otp = models.OTP(email=email, purpose=purpose, code_hash=hashed, expires_at=expires_at)
    db.add(new_otp)
    db.flush()
    new_otp_id = new_otp.id
    db.commit()

    subject = f"Your EduCoffee OTP for {purpose}"
    body = f"Your verification code is: {code}\nThis code will expire in {OTP_EXPIRE_MINUTES} minutes."

    sent = send_email(email, subject, body)
    if not sent:
        # A concurrent resend may already have removed this row. A bulk delete by
        # primary key is safe in either case and avoids ObjectDeletedError.
        db.query(models.OTP).filter(models.OTP.id == new_otp_id).delete(synchronize_session=False)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=(
                "Email sending is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, "
                "SMTP_PASS, and SENDER_EMAIL in the backend environment."
            ),
        )

    return {"detail": "OTP sent"}


@router.post("/verify_otp", status_code=200)
def verify_otp(payload: OTPVerification, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    purpose = payload.purpose
    code = payload.code
    new_password = payload.new_password

    otp = (
        db.query(models.OTP)
        .filter(models.OTP.email == email, models.OTP.purpose == purpose)
        .order_by(models.OTP.created_at.desc())
        .first()
    )
    if not otp:
        raise HTTPException(status_code=404, detail="OTP not found")
    if otp.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")
    if not verify_otp_hash(otp.code_hash, str(code)):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # consume all OTPs for this email+purpose
    if purpose == "reset":
        if not new_password:
            raise HTTPException(status_code=400, detail="New password is required")
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.password = hash_password(new_password)

    db.query(models.OTP).filter(models.OTP.email == email, models.OTP.purpose == purpose).delete()
    db.commit()

    return {"verified": True}


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
def get_student_result(student_id: str, result_id: str, db: Session = Depends(get_db), current_user = Depends(require_student_self_or_admin)):
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
def get_student_results(student_id: str, db: Session = Depends(get_db), current_user = Depends(require_student_self_or_admin)):
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
