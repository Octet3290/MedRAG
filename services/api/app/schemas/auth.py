import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Registration request with input validation constraints."""

    email: EmailStr = Field(
        ...,
        description="User email address (used for login)",
        examples=["researcher@hospital.org"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must be between 8 and 128 characters",
        examples=["SecurePass123!"],
    )


class UserLoginRequest(BaseModel):
    """Login credentials request."""

    email: EmailStr = Field(
        ...,
        description="Registered user email",
        examples=["researcher@hospital.org"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Account password",
    )


class UserResponse(BaseModel):
    """Sanitized public user details schema."""

    id: uuid.UUID
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """JWT Access Token response structure."""

    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse
