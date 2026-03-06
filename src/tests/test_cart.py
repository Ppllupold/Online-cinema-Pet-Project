from decimal import Decimal

import pytest

CART_URL = "/api/v1/cart/"
CART_ITEMS_URL = "/api/v1/cart/movies/"


@pytest.mark.asyncio
async def test_get_cart_create_cart_if_not_exist(auth_client, active_user, db_session):
    await db_session.refresh(active_user, ["cart"])
    assert active_user.cart is None
    response = await auth_client.get(CART_URL)
    assert response.status_code == 200
    assert active_user.cart is not None


@pytest.mark.asyncio
async def test_get_cart_list_empty_cart(auth_client, active_user_with_cart, db_session):
    response = await auth_client.get(CART_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert Decimal(data["total_price"]) == Decimal("0")
    assert data["total_items"] == 0


@pytest.mark.asyncio
async def test_get_cart_items_success(
    auth_client, active_user_with_cart_items, db_session
):
    response = await auth_client.get(CART_URL)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0
    assert data["total_price"] is not None
    assert Decimal(data["total_price"]) == Decimal(
        sum(item.movie.price for item in active_user_with_cart_items.cart.cart_items)
    )
    assert data["total_items"] == len(active_user_with_cart_items.cart.cart_items)


@pytest.mark.asyncio
async def test_add_movie_to_cart_success(
    auth_client, active_user_with_cart, movie_factory, db_session
):
    movie = await movie_factory()
    response = await auth_client.post(f"{CART_ITEMS_URL}{movie.id}")
    assert response.status_code == 201
    assert response.json()["movie_id"] == movie.id


@pytest.mark.asyncio
async def test_add_movie_to_cart_not_found(auth_client, active_user_with_cart):
    response = await auth_client.post(f"{CART_ITEMS_URL}99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_movie_to_cart_duplicate(
    auth_client, active_user_with_cart_items, db_session
):
    cart_item = active_user_with_cart_items.cart.cart_items[0]
    response = await auth_client.post(f"{CART_ITEMS_URL}{cart_item.movie_id}")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_remove_movie_from_cart(
    auth_client, active_user_with_cart_items, db_session
):
    cart_item = active_user_with_cart_items.cart.cart_items[0]
    response = await auth_client.delete(f"{CART_ITEMS_URL}{cart_item.movie_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_clear_cart(auth_client, active_user_with_cart_items, db_session):
    response = await auth_client.delete(CART_URL)
    assert response.status_code == 204
    await db_session.refresh(active_user_with_cart_items.cart, ["cart_items"])
    assert active_user_with_cart_items.cart.cart_items == []
