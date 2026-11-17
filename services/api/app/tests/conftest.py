import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.user import User
from app.repositories.user import user_repo
from app.security.jwt import create_access_token
from app.security.password import hash_password


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provides an unauthenticated async HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def _get_or_create_user(email: str, password: str = "TestPass123!") -> tuple[User, str]:
    """Helper to fetch or register a test user and generate a signed access token."""
    async with AsyncSessionLocal() as session:
        user = await user_repo.get_by_email(session, email=email)
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=email,
                hashed_password=hash_password(password),
                is_active=True,
                is_superuser=False,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        token = create_access_token(subject=user.id)
        return user, token


@pytest.fixture
async def auth_client_a() -> AsyncGenerator[AsyncClient, None]:
    """HTTP Client authenticated as User A."""
    _, token = await _get_or_create_user("user_a@test.local")
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        yield client


@pytest.fixture
async def auth_client_b() -> AsyncGenerator[AsyncClient, None]:
    """HTTP Client authenticated as User B."""
    _, token = await _get_or_create_user("user_b@test.local")
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        yield client
