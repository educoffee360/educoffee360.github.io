from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import logging
import os

import routes
import models  
from database import Base, engine, SessionLocal
from security import hash_password

from models import (
    User,
    Batch,
    Notice,
    Result,
    StudentScore,
    ParentMessage,
    EmailOTP,
    UserDemographic,
    UserRestriction,
    PlanUpgradeRequest,
    BanRequest,
    EmailCampaign,
    Payment,
    Attendance,
    PushSubscription,
    AdCampaign,
    AdImpression,
    PublicPaymentSubmission,
    OfficeAppointment,
)

#Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)

def migrate_user_roles() -> None:
    """Keep the existing PostgreSQL enum compatible with all supported roles."""
    if engine.dialect.name != "postgresql":
        return
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        # 1. Safely initialize the type object if it's completely missing from Supabase
        connection.execute(text("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
                    CREATE TYPE user_role AS ENUM ('teacher', 'student');
                END IF;
            END $$;
        """))

        # 2. Inspect active values
        existing_roles = {
            row[0]
            for row in connection.execute(text(
                "SELECT e.enumlabel FROM pg_type t "
                "JOIN pg_enum e ON t.oid=e.enumtypid "
                "WHERE t.typname='user_role'"
            ))
        }
        
        # 3. Inject missing values seamlessly
        for role_name in ("admin", "moderator"):
            if role_name not in existing_roles:
                connection.execute(text(f"ALTER TYPE user_role ADD VALUE '{role_name}'"))

migrate_user_roles()

def migrate_user_plans() -> None:
    """Normalize legacy subscription names before SQLAlchemy reads User rows.

    Older deployments used Starter/Professional/Elite.  The canonical plans are
    now Free/Pro.  This migration deliberately uses raw SQL so a legacy value
    cannot crash SQLAlchemy's Enum result processor during application startup.
    """
    try:
        if engine.dialect.name == "postgresql":
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                existing = {row[0] for row in connection.execute(text(
                    "SELECT e.enumlabel FROM pg_type t JOIN pg_enum e ON t.oid=e.enumtypid "
                    "WHERE t.typname='user_plan'"
                ))}
                for plan in ("Free", "Pro"):
                    if existing and plan not in existing:
                        connection.execute(text(f"ALTER TYPE user_plan ADD VALUE '{plan}'"))

        # Users are the critical table: normalize legacy values before any ORM query.
        with engine.begin() as connection:
            connection.execute(text("""
            UPDATE users
            SET plan = 'Free'::user_plan
            WHERE plan IS NULL
            """))

            if engine.dialect.name == "postgresql":
                ad_exists = connection.execute(text(
                    "SELECT to_regclass('public.ad_campaigns') IS NOT NULL"
                )).scalar()
                upgrades_exist = connection.execute(text(
                    "SELECT to_regclass('public.plan_upgrade_requests') IS NOT NULL"
                )).scalar()
            else:
                ad_exists = connection.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='ad_campaigns'"
                )).first() is not None
                upgrades_exist = connection.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='plan_upgrade_requests'"
                )).first() is not None

            if ad_exists:
                connection.execute(text("""
                    UPDATE ad_campaigns
                    SET target_plan = CASE
                        WHEN target_plan IN ('Professional', 'Elite', 'Pro', 'pro') THEN 'pro'
                        WHEN target_plan IN ('Starter', 'Free', 'free') THEN 'free'
                        ELSE target_plan
                    END
                    WHERE target_plan IN ('Starter', 'Professional', 'Elite', 'Free', 'Pro', 'free', 'pro')
                """))
            if upgrades_exist:
                connection.execute(text("""
                    UPDATE plan_upgrade_requests
                    SET requested_plan = 'Pro'
                    WHERE requested_plan IN ('Professional', 'Elite', 'Pro')
                """))
    except Exception:
        # Do not hide the original database failure, but make startup resilient on
        # older/local databases where optional legacy tables may not exist yet.
        logger.exception("Could not normalize legacy subscription plan data")
        raise

migrate_user_plans()

def migrate_legacy_plaintext_passwords() -> None:
    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        changed = False
        for user in users:
            if user.password and not str(user.password).startswith("$argon2"):
                user.password = hash_password(user.password)
                changed = True
        if changed:
            db.commit()
    finally:
        db.close()

migrate_legacy_plaintext_passwords()


def ensure_payment_table() -> None:
    """Create the payments table if this deployment does not have it yet."""
    try:
        Payment.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        logger.exception("Could not create the payments table")
        raise


ensure_payment_table()

def ensure_push_subscription_table() -> None:
    """Create the push subscription table if this deployment does not have it yet."""
    try:
        PushSubscription.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        logger.exception("Could not create the push subscriptions table")
        raise


def ensure_attendance_table() -> None:
    """Create the attendance table if the deployment does not yet have the model."""
    try:
        Attendance.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        logger.exception("Could not create the attendance records table")
        raise


def ensure_ad_campaign_table() -> None:
    """Create the ad campaign table if the deployment is missing the ad model."""
    try:
        AdCampaign.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        logger.exception("Could not create the ad campaign table")
        raise


def ensure_ad_impression_table() -> None:
    """Create the one-day ad impression table if the deployment is missing the ad impression model."""
    try:
        AdImpression.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        logger.exception("Could not create the ad impression table")
        raise


ensure_push_subscription_table()
ensure_attendance_table()
ensure_ad_campaign_table()

def ensure_public_request_tables() -> None:
    PublicPaymentSubmission.__table__.create(bind=engine, checkfirst=True)
    OfficeAppointment.__table__.create(bind=engine, checkfirst=True)

ensure_public_request_tables()
ensure_ad_impression_table()

def bootstrap_admin() -> None:
    """Create the first admin from private Render environment variables."""
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    if not email or not password:
        return
    if len(password) < 12:
        logger.warning("ADMIN_PASSWORD must be at least 12 characters; bootstrap skipped")
        return
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.email == email).first()
        if existing:
            if existing.role != "admin":
                logger.warning("ADMIN_EMAIL belongs to a non-admin account; bootstrap skipped")
            return
        db.add(models.User(
            name=os.getenv("ADMIN_NAME", "EduCoffee Admin").strip() or "EduCoffee Admin",
            email=email,
            phone=os.getenv("ADMIN_PHONE", "admin-not-public").strip() or "admin-not-public",
            password=hash_password(password),
            role="admin",
            plan=None,
            batch_codes=None,
        ))
        db.commit()
    finally:
        db.close()


bootstrap_admin()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://educoffee360.github.io",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)

