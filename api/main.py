from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import logging
import os

try:
    from . import routes, models
    from .database import Base, engine, SessionLocal
    from .security import hash_password
except ImportError:  # Support `uvicorn main:app` when launched inside api/.
    import routes
    import models
    from database import Base, engine, SessionLocal
    from security import hash_password

Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)


def migrate_user_roles() -> None:
    """Keep the existing PostgreSQL enum compatible with all supported roles."""
    if engine.dialect.name != "postgresql":
        return
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        existing_roles = {
            row[0]
            for row in connection.execute(text(
                "SELECT e.enumlabel FROM pg_type t "
                "JOIN pg_enum e ON t.oid=e.enumtypid "
                "WHERE t.typname='user_role'"
            ))
        }
        for role_name in ("admin", "moderator"):
            if role_name not in existing_roles:
                connection.execute(text(f"ALTER TYPE user_role ADD VALUE '{role_name}'"))


migrate_user_roles()


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
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)
