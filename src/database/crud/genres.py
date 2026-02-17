from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.movies import Genre, MovieGenresTable
from src.schemas.genres import GenreCreate, GenreUpdate, GenreDetailResponse


async def get_all_genres(db: AsyncSession) -> list[Genre]:
    result = await db.scalars(select(Genre).order_by(Genre.name))
    return list(result.all())


async def get_genre_by_id(db: AsyncSession, genre_id: int) -> Genre:
    genre = await db.get(Genre, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre


async def create_genre(db: AsyncSession, schema: GenreCreate) -> Genre:
    existing = await db.scalar(
        select(Genre).where(func.lower(Genre.name) == schema.name.lower())
    )
    if existing:
        raise HTTPException(status_code=409, detail="Genre already exists")

    genre = Genre(name=schema.name)
    db.add(genre)
    await db.flush()
    await db.refresh(genre)
    return genre


async def update_genre(db: AsyncSession, genre_id: int, schema: GenreUpdate) -> Genre:
    genre = await get_genre_by_id(db, genre_id)

    update_data = schema.model_dump(exclude_unset=True)

    if "name" in update_data:
        existing = await db.scalar(
            select(Genre).where(
                func.lower(Genre.name) == update_data["name"].lower(),
                Genre.id != genre_id,
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Genre already exists")

    for field, value in update_data.items():
        setattr(genre, field, value)

    await db.flush()
    await db.refresh(genre)
    return genre


async def delete_genre(db: AsyncSession, genre_id: int) -> None:
    genre = await get_genre_by_id(db, genre_id)
    await db.delete(genre)
    await db.flush()


async def get_genre_movie_count(db: AsyncSession, genre_id: int) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(MovieGenresTable)
        .where(MovieGenresTable.c.genre_id == genre_id)
    )
    return count or 0
