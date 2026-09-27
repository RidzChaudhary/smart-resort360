from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from pathlib import Path
import os

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")
APP_ENV = os.getenv("APP_ENV", "development").strip().casefold()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    if APP_ENV == "production":
        raise RuntimeError("DATABASE_URL must be configured in production")
    DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'resort360.db').as_posix()}"

# If using PostgreSQL with postgres:// (e.g. older Render/Supabase URL scheme), convert to postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if APP_ENV == "production" and DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("SQLite is not supported in production; configure PostgreSQL")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
