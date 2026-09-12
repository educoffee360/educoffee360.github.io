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
    plan: Optional[Literal['Free', 'Pro']] = None
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

    fee_amount: int = Field(ge=0)
    payment_cycle: Literal['monthly', 'six-months', 'custom']
    custom_period_start: Optional[datetime] = None
    custom_period_end: Optional[datetime] = None

    class Config:
        from_attributes = True

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
    plan: Optional[Literal["Free", "Pro"]] = None

    class Config:
        from_attributes = True


class AdCampaignCreate(BaseModel):
    title: str
    body: str
    image_url: Optional[str] = None
    target_role: Literal['teacher', 'student', 'all'] = 'all'
    target_plan: Literal['free', 'pro', 'all'] = 'free'
    active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class AdCampaignUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    image_url: Optional[str] = None
    target_role: Optional[Literal['teacher', 'student', 'all']] = None
    target_plan: Optional[Literal['free', 'pro', 'all']] = None
    active: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class AdCampaignOut(BaseModel):
    id: str
    title: str
    body: str
    image_url: Optional[str] = None
    target_role: str
    target_plan: str
    active: bool
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdImpressionCreate(BaseModel):
    ad_id: str


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
    requested_plan: Literal["Pro"]
    method: Literal['nagad', 'bkash', 'offline'] = 'nagad'
    trx_id: Optional[str] = Field(default=None, min_length=5, max_length=80)
    payment_phone: Optional[str] = Field(default=None, min_length=8, max_length=30)
    subscription_duration: str = "monthly"


class StaffDecision(BaseModel):
    approved: bool
    note: Optional[str] = Field(default=None, max_length=500)


class PlanSet(BaseModel):
    plan: Literal["Free", "Pro"]


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

class Payment(BaseModel):
    id: str
    student_id: str
    batch_code: str
    amount: int
    status: Literal["paid", "unpaid", "overdue"]
    paid_at: Optional[datetime] = None

    period_start: datetime
    period_end: datetime

    class Config:
        from_attributes = True


class AttendanceRecord(BaseModel):
    student_id: str
    status: Literal['present', 'absent']


class AttendancePayload(BaseModel):
    batch_code: str = Field(min_length=1, max_length=10)
    date: str
    records: List[AttendanceRecord]


class AttendanceStatus(BaseModel):
    student_id: str
    status: Literal['present', 'absent']


class AttendanceUpdate(BaseModel):
    status: Literal['present', 'absent']


class PaymentUpdate(BaseModel):
    status: Literal["paid", "unpaid", "overdue"]


class PublicPaymentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=30)
    plan: Literal['Pro']
    method: Literal['nagad', 'bkash']
    trx_id: str = Field(min_length=5, max_length=80)
    center_name: Optional[str] = Field(default=None, max_length=160)

class OfficeAppointmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=30)
    plan: Literal['Free', 'Pro']
    visit_date: Optional[str] = None


class StatusUpdate(BaseModel):
    status: Literal["pending", "processed", "rejected"]
