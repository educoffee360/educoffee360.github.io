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
    password: str
    role: Literal['teacher', 'student', 'admin']
    batch_codes: Optional[List] = None
    plan: Optional[Literal['Starter', 'Professional', 'Elite']] = None

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
    role: Literal['teacher', 'student', 'admin']
    batch_codes: Optional[List] = None
    plan: Optional[Literal['Starter', 'Professional', 'Elite']] = None

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=40)
    center_name: Optional[str] = Field(default=None, max_length=160)


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
