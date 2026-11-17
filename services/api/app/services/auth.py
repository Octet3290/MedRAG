from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.user import user_repo
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.security.jwt import create_access_token
from app.security.password import hash_password, verify_password


class AuthService:
    """Service layer handling user registration, authentication, and token issuance."""

    async def register(
        self,
        db: AsyncSession,
        *,
        register_in: UserRegisterRequest,
    ) -> TokenResponse:
        existing_user = await user_repo.get_by_email(db, email=register_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists",
            )

        hashed = hash_password(register_in.password)
        user = await user_repo.create(
            db,
            email=register_in.email,
            hashed_password=hashed,
        )

        token = create_access_token(subject=user.id)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    async def authenticate(
        self,
        db: AsyncSession,
        *,
        login_in: UserLoginRequest,
    ) -> TokenResponse:
        user = await user_repo.get_by_email(db, email=login_in.email)

        # Constant-time verification to prevent timing attack enumeration
        if not user or not verify_password(login_in.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user account has been deactivated",
            )

        token = create_access_token(subject=user.id)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )


auth_service = AuthService()
