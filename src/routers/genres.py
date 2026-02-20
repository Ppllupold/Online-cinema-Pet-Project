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


@router.get("/", response_model=list[GenreListResponse])
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


@router.get("/{genre_id}", response_model=GenreDetailResponse)
async def get_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    genre = await genres_crud.get_genre_by_id(db, genre_id)
    movie_count = await genres_crud.get_genre_movie_count(db, genre.id)

    return GenreDetailResponse(
        id=genre.id,
        name=genre.name,
        movie_count=movie_count,
    )


@router.post("/", response_model=GenreDetailResponse, status_code=201)
async def create_genre(schema: GenreCreate, db: AsyncSession = Depends(get_db)):
    genre = await genres_crud.create_genre(db, schema)

    movie_count = await genres_crud.get_genre_movie_count(db, genre.id)
    return GenreDetailResponse(
        id=genre.id,
        name=genre.name,
        movie_count=movie_count,
    )


@router.patch("/{genre_id}", response_model=GenreDetailResponse)
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


@router.delete("/{genre_id}", status_code=204)
async def delete_genre(genre_id: int, db: AsyncSession = Depends(get_db)):
    await genres_crud.delete_genre(db, genre_id)
