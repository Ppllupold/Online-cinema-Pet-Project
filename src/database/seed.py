"""
Database Seeder для заповнення бази фільмами

Використання:
    python seed_database.py

Що робить:
    1. Очищує існуючі дані (опціонально)
    2. Створює certifications, genres, stars, directors
    3. Додає фільми з JSON файлу
"""

import asyncio
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import AsyncSessionLocal
from src.database.models.movies import MovieModel, Genre, Star, Director, Certification


async def clear_database(db: AsyncSession, confirm: bool = False) -> None:
    await db.execute(delete(MovieModel))
    await db.execute(delete(Genre))
    await db.execute(delete(Star))
    await db.execute(delete(Director))
    await db.execute(delete(Certification))
    await db.commit()


async def get_or_create_certification(db: AsyncSession, name: str) -> Certification:
    result = await db.execute(select(Certification).where(Certification.name == name))
    cert = result.scalar_one_or_none()

    if cert is None:
        cert = Certification(name=name)
        db.add(cert)
        await db.flush()

    return cert


async def get_or_create_genre(db: AsyncSession, name: str) -> Genre:
    result = await db.execute(select(Genre).where(Genre.name == name))
    genre = result.scalar_one_or_none()

    if genre is None:
        genre = Genre(name=name)
        db.add(genre)
        await db.flush()

    return genre


async def get_or_create_star(db: AsyncSession, name: str) -> Star:
    result = await db.execute(select(Star).where(Star.name == name))
    star = result.scalar_one_or_none()

    if star is None:
        star = Star(name=name)
        db.add(star)
        await db.flush()

    return star


async def get_or_create_director(db: AsyncSession, name: str) -> Director:
    result = await db.execute(select(Director).where(Director.name == name))
    director = result.scalar_one_or_none()

    if director is None:
        director = Director(name=name)
        db.add(director)
        await db.flush()

    return director


async def seed_movies(db: AsyncSession, movies_data: list[dict]) -> None:
    for idx, movie_data in enumerate(movies_data, 1):

        cert = await get_or_create_certification(db, movie_data["certification"])

        genres = []
        for genre_name in movie_data["genres"]:
            genre = await get_or_create_genre(db, genre_name)
            genres.append(genre)

        stars = []
        for star_name in movie_data["stars"]:
            star = await get_or_create_star(db, star_name)
            stars.append(star)

        directors = []
        for director_name in movie_data["directors"]:
            director = await get_or_create_director(db, director_name)
            directors.append(director)

        movie = MovieModel(
            name=movie_data["name"],
            year=movie_data["year"],
            time=movie_data["time"],
            imdb=movie_data["imdb"],
            votes=movie_data["votes"],
            meta_score=movie_data.get("meta_score"),
            gross=movie_data.get("gross"),
            description=movie_data["description"],
            price=Decimal(str(movie_data["price"])),
            certification=cert,
            genres=genres,
            stars=stars,
            directors=directors,
        )

        db.add(movie)

    await db.commit()


async def main():
    json_file = Path(__file__).parent / "movies_seed_data.json"

    if not json_file.exists():
        return

    with open(json_file, "r", encoding="utf-8") as f:
        movies_data = json.load(f)

    async with AsyncSessionLocal() as db:
        await seed_movies(db, movies_data)


if __name__ == "__main__":
    asyncio.run(main())
