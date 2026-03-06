from decimal import Decimal

import pytest

from src.database.models import Genre, Star, MovieModel, OrderItem, Order
from sqlalchemy import select

from src.database.models.orders import StatusEnum


@pytest.mark.asyncio
async def test_movies_list(client, db_session, movie_factory):
    movies = [await movie_factory() for _ in range(2)]
    response = await client.get("/api/v1/movies/")
    assert response.status_code == 200
    assert response.json()["pagination"] is not None
    assert response.json()["items"] is not None
    assert len(response.json()["items"]) == len(movies)


@pytest.mark.asyncio
async def test_movie_list_pagination(client, db_session, movie_factory):
    movies = [await movie_factory() for _ in range(10)]
    response = await client.get("/api/v1/movies/?page=1&per_page=2")
    assert response.status_code == 200
    pagination = response.json()["pagination"]

    assert pagination["page"] == 1
    assert pagination["per_page"] == 2
    assert pagination["total_pages"] == 5
    assert pagination["total_items"] == 10
    assert pagination["next_page"] is not None
    assert "page=2" in pagination["next_page"]
    assert "per_page=2" in pagination["next_page"]

    response = await client.get("/api/v1/movies/?page=2&per_page=2")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2


@pytest.mark.asyncio
async def test_movies_list_default_sorting(client, db_session, movie_factory):
    films_count = 5
    movies = [await movie_factory(imdb=films_count - 1) for i in range(films_count)]
    movie_imdbs = [movie.imdb for movie in movies]
    response = await client.get("/api/v1/movies/")
    items = response.json()["items"]
    for i in range(len(items)):
        assert movie_imdbs[i] == items[i]["imdb"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sort,order,field,reverse",
    [
        ("imdb", "desc", "imdb", True),
        ("imdb", "asc", "imdb", False),
        ("year", "desc", "year", True),
        ("price", "asc", "price", False),
    ],
)
async def test_movies_sorting(client, movie_factory, sort, order, field, reverse):
    movies = [(await movie_factory()).__dict__ for _ in range(5)]
    movies_sorted = sorted(movies, key=lambda movie: movie[field], reverse=reverse)
    response = await client.get(f"/api/v1/movies/?sort={sort}&order={order}")
    response_items = response.json()["items"]
    for i in range(len(response_items)):
        assert Decimal(response_items[i][field]) == Decimal(movies_sorted[i][field])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filter_field,filter_value,check",
    [
        ("year_gte", 2005, lambda m, v: m["year"] >= v),
        ("imdb_gte", 5.0, lambda m, v: m["imdb"] >= v),
        ("price_lte", Decimal("20"), lambda m, v: m["price"] <= v),
    ],
)
async def test_movies_simple_filters(
    client, movie_factory, filter_field, filter_value, check
):
    movies = [await movie_factory() for _ in range(10)]
    expected = [m for m in movies if check(m.__dict__, filter_value)]

    response = await client.get(f"/api/v1/movies/?{filter_field}={filter_value}")
    response_items = response.json()["items"]
    assert len(response_items) == len(expected)


@pytest.mark.asyncio
async def test_movies_genre_filters_and_logic(client, db_session, movie_factory):
    drama = Genre(name="drama")
    fantasy = Genre(name="fantasy")
    db_session.add_all(
        [
            drama,
            fantasy,
        ]
    )
    await db_session.flush()

    drama_movies = [await movie_factory(genres=[drama]) for _ in range(2)]
    fantasy_movies = [await movie_factory(genres=[fantasy]) for _ in range(2)]
    drama_fantasy_movies = [
        await movie_factory(genres=[drama, fantasy]) for _ in range(2)
    ]

    response_drama = await client.get("/api/v1/movies/", params={"genres": ["drama"]})
    response_items_drama = response_drama.json()["items"]

    assert len(response_items_drama) == 4

    response_drama_fantasy = await client.get(
        "/api/v1/movies/", params={"genres": ["drama", "fantasy"]}
    )
    assert len(response_drama_fantasy.json()["items"]) == 2


@pytest.mark.asyncio
async def test_movies_start_filters_or_logic(client, db_session, movie_factory):
    john = Star(name="john")
    kane = Star(name="kane")
    ralph = Star(name="ralph")
    db_session.add_all([john, kane, ralph])
    await db_session.flush()

    john_movies = [await movie_factory(stars=[john]) for _ in range(2)]
    kane_movies = [await movie_factory(stars=[kane]) for _ in range(2)]
    john_kane_movies = [await movie_factory(stars=[john, kane]) for _ in range(2)]
    ralph_movies = [await movie_factory(stars=[ralph]) for _ in range(2)]

    response_j = await client.get("/api/v1/movies/", params={"stars": ["john"]})
    assert response_j.status_code == 200
    assert len(response_j.json()["items"]) == 4

    response_jk = await client.get(
        "/api/v1/movies/", params={"stars": ["john", "kane"]}
    )
    assert len(response_jk.json()["items"]) == 6


@pytest.mark.asyncio
async def test_search_q(client, db_session, movie_factory):
    await movie_factory(name="The Dark Knight")
    await movie_factory(name="Inception")
    await movie_factory(name="Dark Waters")
    await movie_factory(description="Darkness")
    await movie_factory(description="Dark Princess")

    response = await client.get("/api/v1/movies/", params={"q": "dark"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 4
    names = {item["name"] for item in items}
    assert "The Dark Knight" in names
    assert "Dark Waters" in names


@pytest.mark.asyncio
async def test_get_movie_by_id(client, db_session, movie_factory):
    await movie_factory(name="The Dark Knight")
    await movie_factory(name="The Dark Knight2")
    response = await client.get("/api/v1/movies/1")
    assert response.status_code == 200
    assert response.json()["name"] == "The Dark Knight"
    response = await client.get("/api/v1/movies/3")
    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not Found"


@pytest.mark.asyncio
async def test_get_movie_by_id_404(client, db_session):
    response = await client.get("/api/v1/movies/3")
    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not Found"


@pytest.mark.asyncio
async def test_create_movie_success(client, db_session, movie_factory):
    await movie_factory(name="Just for relations")
    response = await client.post(
        "/api/v1/movies/",
        json={
            "name": "string",
            "year": 2005,
            "time": 100,
            "imdb": 10,
            "votes": 2,
            "price": 2,
            "description": "string",
            "meta_score": 100,
            "gross": 0,
            "certification_id": 1,
            "genre_ids": [1],
            "star_ids": [1],
            "director_ids": [1],
        },
    )
    assert response.status_code == 201
    assert (
        await db_session.scalar(
            select(MovieModel).where(MovieModel.name == response.json()["name"])
        )
    ) is not None


@pytest.mark.asyncio
async def test_create_movie_genre_not_found(client, db_session, movie_factory):
    await movie_factory(name="Just for relations")
    response = await client.post(
        "/api/v1/movies/",
        json={
            "name": "string",
            "year": 2005,
            "time": 100,
            "imdb": 10,
            "votes": 2,
            "price": 2,
            "description": "string",
            "meta_score": 100,
            "gross": 0,
            "certification_id": 1,
            "genre_ids": [1111],
            "star_ids": [1],
            "director_ids": [1],
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Some genres not found"


@pytest.mark.asyncio
async def test_movie_update_success(client, db_session, movie_factory):
    movie = await movie_factory(name="Inception")
    old_year = movie.year
    old_time = movie.time
    response = await client.patch(
        "/api/v1/movies/1",
        json={
            "name": "string",
            "year": 2005,
            "time": 100,
        },
    )
    assert response.status_code == 200
    assert response.json()["name"] == "string"
    assert response.json()["year"] != old_year
    assert response.json()["time"] != old_time


@pytest.mark.asyncio
async def test_movie_full_update_success(client, db_session, movie_factory):
    [await movie_factory() for _ in range(5)]
    response = await client.patch(
        "/api/v1/movies/1",
        json={
            "name": "string",
            "year": 2005,
            "time": 100,
            "imdb": 10,
            "votes": 2,
            "price": 2,
            "description": "string",
            "meta_score": 100,
            "gross": 0,
            "certification_id": 1,
            "genre_ids": [1, 2],
            "star_ids": [3, 4],
            "director_ids": [1, 2, 3],
        },
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_movie_delete(client, db_session, movie_factory):
    await movie_factory(name="Inception")
    response = await client.delete("/api/v1/movies/1")
    assert response.status_code == 204
    response = await client.get("/api/v1/movies/5")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cant_delete_purchased_movie(
    auth_client, active_user, db_session, movie_factory
):
    movie = await movie_factory(name="Inception")
    order = Order(user_id=active_user.id, status=StatusEnum.PAID.value)
    db_session.add(order)
    await db_session.flush()
    await db_session.refresh(order)
    order_item = OrderItem(
        order_id=1, movie_id=movie.id, price_at_order=Decimal("3.33")
    )
    db_session.add(order_item)
    await db_session.flush()
    response = await auth_client.delete("/api/v1/movies/1")
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "You cant delete movies that was purchased at least once"
    )
