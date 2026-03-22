"""
Authentication API router.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    get_current_user,
    get_or_create_user_from_google_claims,
    verify_google_credential,
)
from app.core.database import get_db
from app.models.db_models import User
from app.schemas.schemas import AuthResponse, GoogleAuthRequest, UserResponse


router = APIRouter()


@router.post("/auth/google", response_model=AuthResponse)
def authenticate_with_google(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    claims = verify_google_credential(payload.credential)
    user = get_or_create_user_from_google_claims(claims, db)
    token = create_access_token(user)
    return AuthResponse(access_token=token, user=user)


@router.get("/auth/me", response_model=UserResponse)
def get_authenticated_user(current_user: User = Depends(get_current_user)):
    return current_user
