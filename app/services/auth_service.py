import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.constants.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ADMIN_PASSWORD_ENV,
    ADMIN_USERNAME_ENV,
    INVALID_TOKEN_DETAIL,
    INVALID_TOKEN_SUBJECT_DETAIL,
    JWT_ALGORITHM,
    JWT_SECRET_KEY_ENV,
    MISSING_BEARER_TOKEN_DETAIL,
)
from app.constants.paths import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

bearer_scheme = HTTPBearer(auto_error=False)


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def authenticate_admin(username: str, password: str) -> bool:
    expected_username = _get_required_env(ADMIN_USERNAME_ENV)
    expected_password = _get_required_env(ADMIN_PASSWORD_ENV)

    return hmac.compare_digest(username, expected_username) and hmac.compare_digest(
        password,
        expected_password,
    )


def create_access_token(subject: str) -> str:
    secret_key = _get_required_env(JWT_SECRET_KEY_ENV)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> str:
    secret_key = _get_required_env(JWT_SECRET_KEY_ENV)

    try:
        payload = jwt.decode(token, secret_key, algorithms=[JWT_ALGORITHM])
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_TOKEN_DETAIL,
        ) from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_TOKEN_SUBJECT_DETAIL,
        )

    return subject


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=MISSING_BEARER_TOKEN_DETAIL,
        )

    return verify_access_token(credentials.credentials)
