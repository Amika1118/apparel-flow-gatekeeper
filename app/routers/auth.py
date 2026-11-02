# app/routers/auth.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.errors import AuthenticationError
from app.models import User
from app.schemas import LoginRequest, TokenResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticates user credentials, mitigating user enumeration by returning uniform errors."""
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError("invalid credentials")

    token = create_access_token(user.id, user.role)
    return TokenResponse(
        token=token,
        token_type="bearer",
        role=user.role,
        full_name=user.full_name,
    )


@router.get("/me")
def get_current_user_profile(user: User = Depends(get_current_user)):
    """Retrieves profile details for the currently authenticated user."""
    return {
        "id": user.id,
        "full_name": user.full_name,
        "role": user.role,
    }