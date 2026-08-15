"""
SigmaCloud AI - Database Configuration
SQLAlchemy setup with SQLite (dev) / PostgreSQL (prod)
"""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


def build_engine_kwargs() -> dict:
    """Engine options differ per dialect - SQLite has no real pool to tune."""
    if settings.is_sqlite:
        return {"connect_args": {"check_same_thread": False}}

    return {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        # Managed Postgres (Render/Neon/Supabase) drops idle connections;
        # recycling below their idle timeout avoids "server closed the
        # connection unexpectedly" after the service wakes from sleep.
        "pool_recycle": settings.DB_POOL_RECYCLE_SECONDS,
        "pool_pre_ping": True,
    }


engine = create_engine(settings.DATABASE_URL, **build_engine_kwargs())

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """Session for code outside the request cycle (background jobs, startup).

    Background work must not build its own engine - doing so re-derives
    dialect-specific connect args and leaks pools per job.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
