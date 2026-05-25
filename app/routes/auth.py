from fastapi import APIRouter, HTTPException, status

from app.models import LoginRequest, TokenResponse
from app.services.auth_service import authenticate_admin, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest):
    if not authenticate_admin(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    return TokenResponse(access_token=create_access_token(request.username))
