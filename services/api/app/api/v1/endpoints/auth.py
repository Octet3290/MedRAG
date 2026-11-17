from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.security.deps import get_current_user
from app.services.auth import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    register_in: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user account and immediately issue an access token."""
    return await auth_service.register(db, register_in=register_in)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and get access token",
)
async def login(
    login_in: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email and password and return a signed JWT access token."""
    return await auth_service.authenticate(db, login_in=login_in)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the profile details of the currently authenticated user."""
    return UserResponse.model_validate(current_user)
