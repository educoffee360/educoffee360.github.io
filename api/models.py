from sqlalchemy import Column, String, Enum, Float, Boolean, DateTime, Integer, ForeignKey, JSON, Date, UniqueConstraint
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
    
    role = Column(Enum('teacher', 'student', 'admin', 'moderator', name='user_role'))
    
    batch_codes = Column(JSON, nullable=True)
    
    plan = Column(
    Enum('Free', 'Pro', name='user_plan'),
    nullable=False,
    default='Free'
    )

class AdCampaign(Base):
    __tablename__ = 'ad_campaigns'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    target_role = Column(String, nullable=False, default='all')
    target_plan = Column(String, nullable=False, default='free')
    active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)


class AdImpression(Base):
    __tablename__ = 'ad_impressions'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    ad_id = Column(String, ForeignKey('ad_campaigns.id'), nullable=False)
    seen_date = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'ad_id', 'seen_date', name='uq_ad_impression_day'),
    )

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
        name="payment_cycle",
        default="monthly"
    )

    fee_period_start = Column(DateTime, nullable=True)
    fee_period_end = Column(DateTime, nullable=True)

    # API-facing names used by the batch schema.
    @property
    def custom_period_start(self):
        return self.fee_period_start

    @custom_period_start.setter
    def custom_period_start(self, value):
        self.fee_period_start = value

    @property
    def custom_period_end(self):
        return self.fee_period_end

    @custom_period_end.setter
    def custom_period_end(self, value):
        self.fee_period_end = value

class Notice(Base):
    __tablename__ = 'notices'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    text = Column(String)
    teacher_id = Column(String, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    batch_codes = Column(JSON)

class PushSubscription(Base):
    __tablename__ = 'push_subscriptions'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)

    endpoint = Column(String, nullable=False, unique=True)
    p256dh = Column(String, nullable=False)
    auth = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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

class Attendance(Base):
    __tablename__ = 'attendance_records'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_code = Column(String, ForeignKey('batches.code'), nullable=False, index=True)
    student_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    teacher_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(String(16), nullable=False, default='present')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('batch_code', 'student_id', 'attendance_date', name='uq_attendance_batch_student_date'),
    )


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(String, primary_key=True, default=lambda:str(uuid.uuid4()))

    student_id = Column(String, ForeignKey('users.id'), nullable=False)
    batch_code = Column(String, ForeignKey('batches.code'), nullable=False)

    amount = Column(Integer, nullable=False)

    status = Column(Enum("unpaid", "paid", "overdue"), name="payment_status", default="unpaid", nullable=False)
    paid_at = Column(DateTime, nullable=True)

    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)



class PublicPaymentSubmission(Base):
    __tablename__ = 'public_payment_submissions'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    plan = Column(String, nullable=False)
    method = Column(String, nullable=False)
    trx_id = Column(String, nullable=False)
    center_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default='pending')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class OfficeAppointment(Base):
    __tablename__ = 'office_appointments'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    plan = Column(String, nullable=False)
    visit_date = Column(Date, nullable=True)
    status = Column(String, nullable=False, default='pending')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
