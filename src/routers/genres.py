from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import genres as genres_crud
from src.dependencies.db import get_db
from src.schemas.genres import (
    GenreCreate,
    GenreUpdate,
    GenreListResponse,
    GenreDetailResponse,
)

router = APIRouter(prefix="/genres", tags=["Genres"])


@router.get(
    "/",
    response_model=list[GenreListResponse],
    summary="List all genres",
    description=(
        "Returns a list of all genres with the number of movies in each genre "
        "and a URL to filter movies by that genre."
    ),
    responses={
        200: {"description": "List of genres returned"},
    },
)
async def get_genres(db: AsyncSession = Depends(get_db)):
    genres = await genres_crud.get_all_genres(db)

    result = []
    for genre in genres:
        movie_count = await genres_crud.get_genre_movie_count(db, genre.id)
        result.append(
            GenreListResponse(
                id=genre.id,
                name=genre.name,
                movie_count=movie_count,
                movies_url=f"/api/v1/movies?genres={genre.name.lower()}",
            )
        )

    return result


@router.get(
    "/{genre_id}",
    response_model=GenreDetailResponse,
    summary="Get genre by ID",
    description="Returns detailed information about a single genre including its movie count.",
    responses={
        200: {"description": "Genre details returned"},
        404: {"description": "Genre not found"},
    },
)
async def get_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    genre = await genres_crud.get_genre_by_id(db, genre_id)
    movie_count = await genres_crud.get_genre_movie_count(db, genre.id)

    return GenreDetailResponse(
        id=genre.id,
        name=genre.name,
        movie_count=movie_count,
    )


@router.post(
    "/",
    response_model=GenreDetailResponse,
    status_code=201,
    summary="Create a new genre",
    description="Creates a new genre with the given name. Genre names must be unique.",
    responses={
        201: {"description": "Genre created successfully"},
        400: {"description": "Genre with this name already exists"},
    },
)
async def create_genre(schema: GenreCreate, db: AsyncSession = Depends(get_db)):
    genre = await genres_crud.create_genre(db, schema)

    movie_count = await genres_crud.get_genre_movie_count(db, genre.id)
    return GenreDetailResponse(
        id=genre.id,
        name=genre.name,
        movie_count=movie_count,
    )


@router.patch(
    "/{genre_id}",
    response_model=GenreDetailResponse,
    summary="Update a genre",
    description="Partially updates a genre by ID. Only provided fields will be updated.",
    responses={
        200: {"description": "Genre updated successfully"},
        404: {"description": "Genre not found"},
        400: {"description": "Genre with this name already exists"},
    },
)
async def update_genre(
    genre_id: int, schema: GenreUpdate, db: AsyncSession = Depends(get_db)
):
    genre = await genres_crud.update_genre(db, genre_id, schema)

    movie_count = await genres_crud.get_genre_movie_count(db, genre.id)
    return GenreDetailResponse(
        id=genre.id,
        name=genre.name,
        movie_count=movie_count,
    )


@router.delete(
    "/{genre_id}",
    status_code=204,
    summary="Delete a genre",
    description=(
        "Deletes a genre by ID. "
        "If the genre is associated with movies, those associations will be removed as well."
    ),
    responses={
        204: {"description": "Genre deleted successfully"},
        404: {"description": "Genre not found"},
    },
)
async def delete_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    await genres_crud.delete_genre(db, genre_id)