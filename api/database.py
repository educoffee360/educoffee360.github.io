import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Fetch the URL from environment variables. 
# Fall back to a local SQLite file so you don't leak secrets on GitHub!
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local_app.db")

# 2. Fix Render/Heroku dialect issue if using a cloud PostgreSQL URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. Create the engine
# Note: connect_args is only needed for SQLite, so we conditionally apply it
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()