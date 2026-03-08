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


@router.get(
    "/",
    response_model=MovieListResponse,
    summary="List movies with filters and pagination",
    description=(
        "Returns a paginated list of movies. Supports filtering by genre, actors, director, "
        "year, IMDB rating, and price. Genre filter uses AND logic (movie must have all specified genres). "
        "Actors filter uses OR logic (movie must have at least one of the specified actors). "
        "Results can be sorted by year, imdb, or price in ascending or descending order."
    ),
    responses={
        200: {"description": "Paginated list of movies returned"},
    },
)
async def get_movies(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    sort: movies_crud.SortField = Query("imdb", description="Sort field: year, imdb, price"),
    order: movies_crud.SortOrder = Query("desc", description="Sort order: asc, desc"),
    genres: list[str] | None = Query(None, description="Filter by genres (AND logic)"),
    stars: list[str] | None = Query(None, description="Filter by actors (OR logic)"),
    filters: MovieFilterSchema = Depends(),
    db: AsyncSession = Depends(get_db),
):
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


@router.get(
    "/{movie_id}",
    response_model=MovieDetailResponse,
    summary="Get movie by ID",
    description=(
        "Returns full details of a single movie including genres, cast, director, "
        "certification, and pricing information."
    ),
    responses={
        200: {"description": "Movie details returned"},
        404: {"description": "Movie not found"},
    },
)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await movies_crud.get_movie_by_id(movie_id, db)
    return MovieDetailResponse.model_validate(movie)


@router.post(
    "/",
    response_model=MovieDetailResponse,
    status_code=201,
    summary="Create a new movie",
    description=(
        "Creates a new movie with all related data. "
        "Requires at least one genre, one actor, and one director. "
        "All provided IDs (genre_ids, star_ids, director_ids, certification_id) must exist in the database."
    ),
    responses={
        201: {"description": "Movie created successfully"},
        400: {"description": "Invalid data or referenced entity not found"},
    },
)
async def create_movie(schema: MovieCreate, db: AsyncSession = Depends(get_db)):
    movie = await movies_crud.create_movie(schema, db)
    return MovieDetailResponse.model_validate(movie)


@router.patch(
    "/{movie_id}",
    response_model=MovieDetailResponse,
    summary="Update a movie",
    description=(
        "Partially updates a movie by ID. All fields are optional. "
        "Providing genre_ids, star_ids, or director_ids will replace the existing associations entirely."
    ),
    responses={
        200: {"description": "Movie updated successfully"},
        404: {"description": "Movie not found"},
        400: {"description": "Invalid data or referenced entity not found"},
    },
)
async def update_movie(
    movie_id: int, schema: MovieUpdate, db: AsyncSession = Depends(get_db)
):
    movie = await movies_crud.update_movie(movie_id, schema, db)
    return MovieDetailResponse.model_validate(movie)


@router.delete(
    "/{movie_id}",
    status_code=204,
    summary="Delete a movie",
    description="Deletes a movie by ID along with all its genre, actor, and director associations.",
    responses={
        204: {"description": "Movie deleted successfully"},
        404: {"description": "Movie not found"},
    },
)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    await movies_crud.delete_movie(movie_id, db)