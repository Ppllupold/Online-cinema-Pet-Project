import asyncio
import os
from decimal import Decimal

import pytest
import pytest_asyncio
from faker import Faker
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from main import app
from src.database.models import (
    MovieModel,
    Certification,
    Genre,
    Star,
    Director,
    Cart,
    CartItem,
    OrderItem,
    Order,
)
from src.database.models.accounts import (
    UserGroupEnum,
    UserGroup,
    UserModel,
    ActivationTokenModel,
    RefreshTokenModel,
)
from src.database.models.base import Base
from src.dependencies.db import get_db
from src.services.jwt import jwt_manager

fake = Faker()
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
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
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
    token = RefreshTokenModel(
        user_id=user.id, token=jwt_manager.create_refresh_token(user.id)
    )
    db_session.add(token)
    await db_session.refresh(user, ["refresh_tokens"])
    return user


@pytest_asyncio.fixture
async def active_user_with_cart(db_session: AsyncSession, active_user):
    db_session.add(Cart(user_id=active_user.id))
    await db_session.flush()
    await db_session.refresh(active_user, ["cart"])
    return active_user


@pytest_asyncio.fixture
async def auth_client(
    client: AsyncClient, db_session: AsyncSession, active_user: UserModel
):
    token = jwt_manager.create_access_token(active_user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def active_user_with_cart_items(
    db_session: AsyncSession, active_user_with_cart: UserModel, movie_factory
):
    movies = [await movie_factory() for _ in range(3)]
    for movie in movies:
        db_session.add(
            CartItem(cart_id=active_user_with_cart.cart.id, movie_id=movie.id)
        )
    await db_session.flush()
    await db_session.refresh(active_user_with_cart.cart, ["cart_items"])
    return active_user_with_cart


@pytest_asyncio.fixture
async def movie_factory(db_session: AsyncSession):
    async def create_movie(**kwargs) -> MovieModel:
        certification = Certification(name=fake.unique.word())
        db_session.add(certification)
        await db_session.flush()

        genre = Genre(name=fake.unique.word())
        star = Star(name=fake.name())
        director = Director(name=fake.name())
        db_session.add_all([genre, star, director])
        await db_session.flush()

        movie = MovieModel(
            name=kwargs.get("name", fake.sentence(nb_words=3)),
            year=kwargs.get("year", 2000),
            time=kwargs.get("time", 120),
            imdb=kwargs.get("imdb", 7.0),
            votes=kwargs.get("votes", 1000),
            price=kwargs.get("price", Decimal("9.99")),
            description=kwargs.get("description", fake.text()),
            certification_id=certification.id,
        )
        movie.genres = kwargs.get("genres", [genre])
        movie.stars = kwargs.get("stars", [star])
        movie.directors = [director]

        db_session.add(movie)
        await db_session.flush()
        await db_session.refresh(
            movie, ["genres", "stars", "directors", "certification"]
        )
        return movie

    return create_movie


@pytest_asyncio.fixture
async def create_valid_order(
    db_session: AsyncSession, active_user_with_cart_items: UserModel
):
    valid_order = Order(
        user_id=active_user_with_cart_items.id,
        total_amount=Decimal(
            sum(
                cart_item.movie.price
                for cart_item in active_user_with_cart_items.cart.cart_items
            )
        ),
    )
    db_session.add(valid_order)
    await db_session.flush()
    await db_session.refresh(valid_order)

    order_items = [
        OrderItem(
            order_id=valid_order.id,
            movie_id=item.movie_id,
            price_at_order=item.movie.price,
        )
        for item in active_user_with_cart_items.cart.cart_items
    ]
    db_session.add_all(order_items)
    await db_session.flush()
    await db_session.refresh(valid_order, ["order_items"])
    return valid_order
