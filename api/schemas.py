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
    role: Literal['teacher', 'student']
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
    absent: bool
    seen_by_guardian: bool

class Result(BaseModel):
    title: str
    description: Optional[str] 
    total_marks: int 
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
    role: Literal['teacher', 'student']
    batch_codes: Optional[List] = None

    class Config:
        from_attributes = True