from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
