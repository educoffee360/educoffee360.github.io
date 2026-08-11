from pydantic import BaseModel, Field, EmailStr
from typing import Literal, Optional, List
from datetime import datetime
from uuid import UUID

class User(BaseModel):
    name: str
    id: Optional[UUID] = None
    email: EmailStr
    center_name: Optional[str] = None
    phone: str
    password: str = Field(min_length=6, max_length=128)
    role: Literal['teacher', 'student', 'admin', 'moderator']
    batch_codes: Optional[List] = None
    plan: Optional[Literal['Starter', 'Professional', 'Elite']] = None
    verification_token: str
    location: Optional[str] = Field(default=None, max_length=120)
    grade: Optional[str] = Field(default=None, max_length=80)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Batch(BaseModel):
    name: str
    year: str 
    schedule: str
    code: str = Field(min_length=6, max_length=6)
    teacher_id: str

class StudentScore(BaseModel):
    student_id: str
    marks: Optional[float] = None
    remarks: Optional[str] = ''
    absent: bool = False
    seen_by_guardian: bool = False

class Result(BaseModel):
    title: str
    description: Optional[str] = None
    total_marks: int = Field(gt=0)
    batch_code: str = Field(min_length=6, max_length=6)
    scores: List[StudentScore]

class Notice(BaseModel):
    id: Optional[str] = None
    text: str
    teacher_id: str
    batch_codes: List[str]
    created_at: Optional[datetime] = None

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    center_name: Optional[str] = None
    phone: str
    role: Literal['teacher', 'student', 'admin', 'moderator']
    batch_codes: Optional[List] = None
    plan: Optional[Literal['Starter', 'Professional', 'Elite']] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=40)
    center_name: Optional[str] = Field(default=None, max_length=160)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class PasswordReset(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=6, max_length=128)


class ParentMessageCreate(BaseModel):
    student_id: str
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=5000)


class ParentBroadcastCreate(BaseModel):
    batch_codes: List[str] = Field(default_factory=list)
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=5000)


class ParentMessageResponse(BaseModel):
    id: str
    teacher_id: str
    teacher_name: str
    student_id: str
    subject: str
    body: str
    batch_codes: List[str]
    created_at: datetime


class OTPSendRequest(BaseModel):
    email: EmailStr
    purpose: Literal['register', 'password_reset'] = 'register'


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r'^\d{6}$')
    purpose: Literal['register', 'password_reset'] = 'register'


class PlanUpgradeCreate(BaseModel):
    requested_plan: Literal['Professional', 'Elite']
    method: Literal['nagad', 'offline'] = 'nagad'
    trx_id: Optional[str] = Field(default=None, min_length=5, max_length=80)
    payment_phone: Optional[str] = Field(default=None, min_length=8, max_length=30)


class StaffDecision(BaseModel):
    approved: bool
    note: Optional[str] = Field(default=None, max_length=500)


class PlanSet(BaseModel):
    plan: Literal['Starter', 'Professional', 'Elite']


class BanAction(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class StaffEmailCreate(BaseModel):
    recipient_ids: List[str] = Field(min_length=1, max_length=50)
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=5000)


class ModeratorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=40)
    password: str = Field(min_length=8, max_length=128)
