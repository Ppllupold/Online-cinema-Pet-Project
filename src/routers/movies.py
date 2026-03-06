# src/routers/movies.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.db import get_db
from src.database.crud import movies as movies_crud
from src.schemas.movies import (
    MovieFilterSchema,
    MovieListResponse,
    MovieDetailResponse,
    MovieCreate,
    MovieUpdate,
)

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("/", response_model=MovieListResponse)
async def get_movies(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    sort: movies_crud.SortField = Query("imdb", description="Sort by field"),
    order: movies_crud.SortOrder = Query("desc", description="Sort order"),
    genres: list[str] | None = Query(None),
    stars: list[str] | None = Query(None),
    filters: MovieFilterSchema = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of movies

    **Filters:**
    - `q`: Search by name or description
    - `year_gte`: Minimum year
    - `imdb_gte`: Minimum IMDB rating
    - `price_lte`: Maximum price
    - `genres`: Filter by genres (AND logic - all required)
    - `stars`: Filter by actors (OR logic - any match)
    - `director`: Filter by director name

    **Sorting:**
    - `sort`: year, imdb, price
    - `order`: asc, desc
    """
    filters.genres = genres
    filters.stars = stars

    return await movies_crud.get_movies_list(
        db,
        page=page,
        per_page=per_page,
        filters=filters,
        sort=sort,
        order=order,
    )


@router.get("/{movie_id}", response_model=MovieDetailResponse)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    """Get movie details by ID"""

    movie = await movies_crud.get_movie_by_id(movie_id, db)
    return MovieDetailResponse.model_validate(movie)


@router.post("/", response_model=MovieDetailResponse, status_code=201)
async def create_movie(schema: MovieCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new movie

    **Required:**
    - All basic movie fields
    - `certification_id`
    - `genre_ids` (at least 1)
    - `star_ids` (at least 1)
    - `director_ids` (at least 1)
    """

    movie = await movies_crud.create_movie(schema, db)
    return MovieDetailResponse.model_validate(movie)


@router.patch("/{movie_id}", response_model=MovieDetailResponse)
async def update_movie(
    movie_id: int, schema: MovieUpdate, db: AsyncSession = Depends(get_db)
):
    """
    Update movie (partial update)

    All fields are optional.
    """

    movie = await movies_crud.update_movie(movie_id, schema, db)
    return MovieDetailResponse.model_validate(movie)


@router.delete("/{movie_id}", status_code=204)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    await movies_crud.delete_movie(movie_id, db)
