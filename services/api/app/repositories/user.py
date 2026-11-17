import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Repository managing User entity persistence."""

    async def create(
        self,
        db: AsyncSession,
        *,
        email: str,
        hashed_password: str,
        is_superuser: bool = False,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=is_superuser,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> User | None:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(
        self,
        db: AsyncSession,
        *,
        email: str,
    ) -> User | None:
        query = select(User).where(User.email == email.strip().lower())
        result = await db.execute(query)
        return result.scalar_one_or_none()


user_repo = UserRepository()
