"""
JWT helper utilities.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt

from config.settings import get_settings
from utility.errors import ApiError


settings = get_settings()


def _create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: str,
    email: Optional[str] = None,
    role: Optional[str] = None,
) -> str:
    """
    Build a JWT token for the provided subject.
    """

    payload = {
        "sub": subject,
        "type": token_type,
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + expires_delta,
    }
    if email:
        payload["email"] = email
    if role:
        payload["role"] = role
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def generate_token_pair(
    subject: str, email: Optional[str] = None, role: Optional[str] = None
) -> Dict[str, str]:
    """
    Create an access and refresh token for the given subject.
    """

    access_token = _create_token(
        subject=subject,
        expires_delta=timedelta(minutes=settings.access_token_exp_minutes),
        token_type="access",
        email=email,
        role=role,
    )
    refresh_token = _create_token(
        subject=subject,
        expires_delta=timedelta(minutes=settings.refresh_token_exp_minutes),
        token_type="refresh",
        email=email,
        role=role,
    )
    return {"access_token": access_token, "refresh_token": refresh_token}


def get_subject_from_access_token(token: str) -> str:
    """
    Decode an access token and return the subject (admin/inspector id).
    """

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:  # type: ignore[attr-defined]
        raise ApiError("Token has expired", 401, "token_expired") from exc
    except jwt.InvalidTokenError as exc:  # type: ignore[attr-defined]
        raise ApiError("Invalid token", 401, "invalid_token") from exc

    token_type = payload.get("type")
    if token_type != "access":
        raise ApiError("Invalid token type", 401, "invalid_token_type")

    subject = payload.get("sub")
    if not subject:
        raise ApiError("Invalid token payload", 401, "invalid_token_payload")

    return str(subject)


def decode_access_token(token: str) -> Dict[str, any]:
    """
    Decode an access token and return the full payload.
    Useful for getting email, role, and other token claims.
    """

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:  # type: ignore[attr-defined]
        raise ApiError("Token has expired", 401, "token_expired") from exc
    except jwt.InvalidTokenError as exc:  # type: ignore[attr-defined]
        raise ApiError("Invalid token", 401, "invalid_token") from exc

    token_type = payload.get("type")
    if token_type != "access":
        raise ApiError("Invalid token type", 401, "invalid_token_type")

    return payload

