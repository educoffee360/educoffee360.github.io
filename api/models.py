from sqlalchemy import Column, String, Enum, Float, Boolean, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
try:
    from .database import Base
except ImportError:
    from database import Base
import uuid
from datetime import datetime
# from typing import List

class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    center_name = Column(String, nullable=True)
    email = Column(String, unique=True)
    phone = Column(String)
    password = Column(String)
    
    # FIX: Added name='user_role'
    role = Column(Enum('teacher', 'student', 'admin', name='user_role'))
    
    batch_codes = Column(JSON, nullable=True)
    
    # FIX: Added name='user_plan'
    plan = Column(Enum('Starter', 'Professional', 'Elite', name='user_plan'), nullable=True)

class Batch(Base):
    __tablename__ = 'batches'

    code = Column(String(6), primary_key=True)
    name = Column(String)
    year = Column(String)
    schedule = Column(String)
    teacher_id = Column(String, ForeignKey('users.id'))

class Notice(Base):
    __tablename__ = 'notices'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    text = Column(String)
    teacher_id = Column(String, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    batch_codes = Column(JSON)

class Result(Base):
    __tablename__ = 'results'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    description = Column(String, nullable=True)
    total_marks = Column(Integer)
    batch_code = Column(String, ForeignKey('batches.code'))

    scores = relationship("StudentScore", back_populates="result")

class StudentScore(Base):
    __tablename__ = 'student_scores'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    result_id = Column(String, ForeignKey('results.id'))
    student_id = Column(String, ForeignKey('users.id'))

    marks = Column(Float, nullable=True)
    remarks = Column(String, nullable=True)
    absent = Column(Boolean, default=False)
    seen_by_guardian = Column(Boolean, default=False)

    result = relationship("Result", back_populates="scores")
