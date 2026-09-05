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
    role = Column(Enum('teacher', 'student', 'admin', 'moderator', name='user_role'))
    
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

    fee_amount = Column(Integer, nullable=False)

    payment_cycle = Column(
        Enum("monthly", "six-months", "custom"),
        nullable=False,
        default="monthly"
    )

    fee_period_start = Column(DateTime, nullable=True)
    fee_period_end = Column(DateTime, nullable=True)

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


class ParentMessage(Base):
    __tablename__ = 'parent_messages'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_id = Column(String, ForeignKey('users.id'), nullable=False)
    student_id = Column(String, ForeignKey('users.id'), nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    batch_codes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EmailOTP(Base):
    __tablename__ = 'email_otps'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, nullable=False, index=True)
    purpose = Column(String, nullable=False, default='register')
    code_hash = Column(String, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)


class UserDemographic(Base):
    __tablename__ = 'user_demographics'

    user_id = Column(String, ForeignKey('users.id'), primary_key=True)
    location = Column(String, nullable=True, index=True)
    grade = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserRestriction(Base):
    __tablename__ = 'user_restrictions'

    user_id = Column(String, ForeignKey('users.id'), primary_key=True)
    banned = Column(Boolean, nullable=False, default=False)
    reason = Column(String, nullable=True)
    banned_by = Column(String, ForeignKey('users.id'), nullable=True)
    banned_at = Column(DateTime, nullable=True)


class PlanUpgradeRequest(Base):
    __tablename__ = 'plan_upgrade_requests'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    requested_plan = Column(String, nullable=False)
    method = Column(String, nullable=False, default='nagad')
    trx_id = Column(String, nullable=True, unique=True, index=True)
    payment_phone = Column(String, nullable=True)
    status = Column(String, nullable=False, default='pending', index=True)
    review_note = Column(String, nullable=True)
    reviewed_by = Column(String, ForeignKey('users.id'), nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)


class BanRequest(Base):
    __tablename__ = 'ban_requests'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    target_user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    requested_by = Column(String, ForeignKey('users.id'), nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, nullable=False, default='pending', index=True)
    reviewed_by = Column(String, ForeignKey('users.id'), nullable=True)
    review_note = Column(String, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)


class EmailCampaign(Base):
    __tablename__ = 'email_campaigns'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = Column(String, ForeignKey('users.id'), nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    recipient_count = Column(Integer, nullable=False, default=0)
    sent_count = Column(Integer, nullable=False, default=0)
    failed_recipients = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Payment(Base):

    id = Column(String, primary_key=True, default=lambda:str(uuid.uuid4()))

    student_id = Column(String, ForeignKey('users.id'), nullable=False)
    batch_code = Column(String, ForeignKey('batches.code'), nullable=False)

    status = Column(Enum("unpaid", "paid", "overdue"), default="unpaid", nullable=False)
    paid_at = Column(DateTime, nullable=True)

    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)