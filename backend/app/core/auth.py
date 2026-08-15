"""
Authentication helpers for Google sign-in and app JWT sessions.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.db_models import User


logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def create_access_token(user: User) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "exp": expire_at,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_google_credential(credential: str) -> dict:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication is not configured on the backend.",
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=settings.GOOGLE_CLOCK_SKEW_SECONDS,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google credential: {exc}",
        ) from exc

    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google issuer")
    if not claims.get("email") or not claims.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google account data is incomplete")
    if not claims.get("email_verified", False):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google email is not verified")
    return claims


def get_or_create_user_from_google_claims(claims: dict, db: Session) -> User:
    user = db.query(User).filter(User.google_sub == claims["sub"]).first()
    if not user:
        user = db.query(User).filter(User.email == claims["email"]).first()

    if user:
        user.google_sub = claims["sub"]
        user.email = claims["email"]
        user.name = claims.get("name") or claims["email"]
        user.picture = claims.get("picture")
    else:
        user = User(
            google_sub=claims["sub"],
            email=claims["email"],
            name=claims.get("name") or claims["email"],
            picture=claims.get("picture"),
        )
        db.add(user)

    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = int(payload.get("sub", "0"))
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# Additive column upgrades applied at startup.
#
# SQLAlchemy's create_all() creates missing TABLES but never alters existing
# ones, so a column added to a model after a database already exists would be
# missing at runtime. This keeps deployed instances working across upgrades
# without a migration tool; Alembic is the right answer once schema changes
# stop being purely additive.
_COLUMN_UPGRADES: dict[str, dict[str, str]] = {
    "datasets": {
        "user_id": "INTEGER",
    },
    "training_jobs": {
        "user_id": "INTEGER",
        "progress_message": "VARCHAR(255)",
    },
    "trained_models": {
        "user_id": "INTEGER",
    },
}


def ensure_auth_schema(engine: Engine) -> None:
    """Add any columns missing from tables that already exist."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table, columns in _COLUMN_UPGRADES.items():
        if table not in existing_tables:
            continue

        present = {column["name"] for column in inspector.get_columns(table)}
        missing = {name: sql_type for name, sql_type in columns.items() if name not in present}
        if not missing:
            continue

        with engine.begin() as connection:
            for name, sql_type in missing.items():
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
                logger.info("Schema upgrade: added %s.%s", table, name)
