from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

import schemas
import models
from database import get_db

from security import hash_password, verify_password, needs_rehash, create_access_token, decode_access_token
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

router = APIRouter(prefix="/api")

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
    if not verify_password(db_user.password, user.password):
        raise HTTPException(401, "Incorrect password")
    if needs_rehash(db_user.password):
        new_hash = hash_password(user.password)
        db_user.password = new_hash

        db.commit()
        db.refresh(db_user)

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
def get_all_batches(db: Session = Depends(get_db), current_user = Depends(require_role("teacher", "admin"))):
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
    db.commit()
    db.refresh(new_batch)
    return new_batch


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

@router.get('/students_in_batch/{batch_code}', response_model=List[schemas.User], status_code=200)
def get_students_in_batch(batch_code, db: Session = Depends(get_db), current_user = Depends(require_batch_teacher_or_admin)):
    batch = db.query(models.Batch).filter(models.Batch.code == batch_code).first()
    if not batch:
        raise HTTPException(404, 'Batch not found')
    
    students = db.query(models.User).filter(models.User.role == 'student').all()
    students_in_batch = []
    for student in students:
        if batch_code in student.batch_codes:
            students_in_batch.append(student)

    return students_in_batch

@router.get('/my_students/{teacher_id}', response_model=List[schemas.User], status_code=200)
def get_my_students(teacher_id, db: Session = Depends(get_db), current_user = Depends(require_teacher_self_or_admin)):
    my_batches = db.query(models.Batch).filter(models.Batch.teacher_id == teacher_id)
    my_batches_codes = []
    for batch in my_batches:
        my_batches_codes.append(batch.code)

    students = db.query(models.User).filter(models.User.role == 'student').all()
    my_students = []
    for student in students:
        for bc in student.batch_codes:
            if bc in my_batches_codes:
                my_students.append(student)
    
    return my_students

@router.get("/results", response_model=List[schemas.Result], status_code=200)
def get_all_results(db: Session = Depends(get_db), current_user = Depends(require_role("teacher", "admin"))):
    return db.query(models.Result).all()

@router.post('/new_result', status_code=201)
def create_result(result: schemas.Result, db: Session = Depends(get_db), current_user = Depends(require_teacher_or_admin)):
    batch = db.query(models.Batch).filter(models.Batch.code == result.batch_code).first()
    if not batch:
        raise HTTPException(404, 'Batch not found')

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
        for batch_code in student.batch_codes:
            if batch_code in notice.batch_codes:
                filtered_notices.append(notice)
    return filtered_notices


@router.post("/new_notice", response_model=schemas.Notice, status_code=201)
def create_new_notice(notice: schemas.Notice, db: Session = Depends(get_db), current_user = Depends(require_teacher_or_admin)):
    new_notice = models.Notice(
        text=notice.text,
        teacher_id=notice.teacher_id,
        batch_codes=notice.batch_codes,
        created_at=notice.created_at,
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
    db_notice.teacher_id = notice.teacher_id
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

