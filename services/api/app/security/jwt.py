import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings


def create_access_token(
    subject: str | uuid.UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Generate a signed JWT access token.
    Claims:
      - sub: Subject identifier (User UUID)
      - iat: Issued at timestamp (UTC)
      - exp: Expiration timestamp (UTC)
    """
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and cryptographically verify a JWT access token.
    Raises jwt.PyJWTError on expiration, tampering, or invalid signature.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"require": ["sub", "exp", "iat"]},
    )
