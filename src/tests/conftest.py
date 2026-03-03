import os
import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_TEST_PATH = PROJECT_ROOT / ".env.test"

load_dotenv(ENV_TEST_PATH)


from src.database.models.base import Base
from src.dependencies.db import get_db
from src.services.jwt import jwt_manager
from main import app
from src.database.models.accounts import (
    UserGroupEnum,
    UserGroup,
    UserModel,
    ActivationTokenModel,
    RefreshTokenModel,
)

TEST_DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}"
    f"/{os.getenv('POSTGRES_DB')}"
)

# Test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Event loop для async тестів"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """
    Database session для тесту

    - Створює таблиці
    - Після тесту очищує
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        groupes = [
            UserGroup(name=UserGroupEnum.USER),
            UserGroup(name=UserGroupEnum.MODERATOR),
            UserGroup(name=UserGroupEnum.ADMIN),
        ]
        session.add_all(groupes)
        await session.commit()
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """HTTP client для тестування API"""

    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def register_user(db_session: AsyncSession):
    user = UserModel(email="user@gmail.com", group_id=1)
    user.password = "8f6@E6hR~<T1w"
    db_session.add(user)
    await db_session.flush()
    token = ActivationTokenModel(user_id=user.id)
    db_session.add(token)
    await db_session.refresh(user, ["activation_token"])
    return user


@pytest_asyncio.fixture
async def active_user(db_session: AsyncSession):
    user = UserModel(email="user@gmail.com", group_id=1)
    user.password = "8f6@E6hR~<T1w"
    user.is_active = True
    db_session.add(user)
    await db_session.flush()
    token = RefreshTokenModel(user_id=user.id, token=jwt_manager.create_refresh_token(user.id))
    db_session.add(token)
    await db_session.refresh(user, ["refresh_tokens"])
    return user

@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, db_session: AsyncSession, active_user: UserModel):
    token = jwt_manager.create_access_token(active_user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return client