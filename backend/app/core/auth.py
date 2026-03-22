"""
Authentication helpers for Google sign-in and app JWT sessions.
"""
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


def ensure_auth_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if "users" not in existing_tables:
        return

    table_columns = {
        table: {column["name"] for column in inspector.get_columns(table)}
        for table in ("datasets", "training_jobs", "trained_models")
        if table in existing_tables
    }

    with engine.begin() as connection:
        if "datasets" in table_columns and "user_id" not in table_columns["datasets"]:
            connection.execute(text("ALTER TABLE datasets ADD COLUMN user_id INTEGER"))
        if "training_jobs" in table_columns and "user_id" not in table_columns["training_jobs"]:
            connection.execute(text("ALTER TABLE training_jobs ADD COLUMN user_id INTEGER"))
        if "trained_models" in table_columns and "user_id" not in table_columns["trained_models"]:
            connection.execute(text("ALTER TABLE trained_models ADD COLUMN user_id INTEGER"))
