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

# Імпорти з твого проекту (потрібно буде налаштувати шляхи!)
# from src.database.session import AsyncSessionLocal
# from src.database.models import (
#     MovieModel, Genre, Star, Director, Certification
# )

# ========================================================================
# НАЛАШТУВАННЯ ШЛЯХІВ - ЗМІНИ ПІД СВІЙ ПРОЕКТ!
# ========================================================================

# Якщо скрипт в корені проекту, розкоментуй:
# import sys
# sys.path.insert(0, str(Path(__file__).parent))

# Потім імпортуй свої модулі:
from src.database.session import AsyncSessionLocal
from src.database.models.movies import MovieModel, Genre, Star, Director, Certification

# ========================================================================
# HELPER ФУНКЦІЇ
# ========================================================================


async def clear_database(db: AsyncSession, confirm: bool = False) -> None:
    """
    Очищує всі дані з таблиць.

    УВАГА: Видаляє ВСІ фільми, жанри, акторів, режисерів!
    """
    if not confirm:
        print(
            "⚠️  Очищення БД вимкнено. Для ввімкнення: clear_database(db, confirm=True)"
        )
        return

    print("🗑️  Очищення бази даних...")

    # Видаляємо в правильному порядку (через CASCADE воно саме видалить зв'язки)
    await db.execute(delete(MovieModel))
    await db.execute(delete(Genre))
    await db.execute(delete(Star))
    await db.execute(delete(Director))
    await db.execute(delete(Certification))

    await db.commit()
    print("✅ База очищена!")


async def get_or_create_certification(db: AsyncSession, name: str) -> Certification:
    """Знаходить або створює certification."""
    result = await db.execute(select(Certification).where(Certification.name == name))
    cert = result.scalar_one_or_none()

    if cert is None:
        cert = Certification(name=name)
        db.add(cert)
        await db.flush()  # Щоб отримати ID

    return cert


async def get_or_create_genre(db: AsyncSession, name: str) -> Genre:
    """Знаходить або створює жанр."""
    result = await db.execute(select(Genre).where(Genre.name == name))
    genre = result.scalar_one_or_none()

    if genre is None:
        genre = Genre(name=name)
        db.add(genre)
        await db.flush()

    return genre


async def get_or_create_star(db: AsyncSession, name: str) -> Star:
    """Знаходить або створює актора."""
    result = await db.execute(select(Star).where(Star.name == name))
    star = result.scalar_one_or_none()

    if star is None:
        star = Star(name=name)
        db.add(star)
        await db.flush()

    return star


async def get_or_create_director(db: AsyncSession, name: str) -> Director:
    """Знаходить або створює режисера."""
    result = await db.execute(select(Director).where(Director.name == name))
    director = result.scalar_one_or_none()

    if director is None:
        director = Director(name=name)
        db.add(director)
        await db.flush()

    return director


# ========================================================================
# ГОЛОВНА ФУНКЦІЯ SEED
# ========================================================================


async def seed_movies(db: AsyncSession, movies_data: list[dict]) -> None:
    """
    Додає фільми з JSON даних.

    Формат JSON:
    {
        "name": "Movie Name",
        "year": 2020,
        "time": 120,
        "imdb": 8.5,
        "votes": 1000000,
        "meta_score": 75.0,
        "gross": 100.0,
        "description": "...",
        "price": 9.99,
        "certification": "PG-13",
        "genres": ["Action", "Drama"],
        "stars": ["Actor 1", "Actor 2"],
        "directors": ["Director 1"]
    }
    """
    print(f"\n📽️  Додаємо {len(movies_data)} фільмів...\n")

    for idx, movie_data in enumerate(movies_data, 1):
        print(f"[{idx}/{len(movies_data)}] {movie_data['name']} ({movie_data['year']})")

        # 1. Certification
        cert = await get_or_create_certification(db, movie_data["certification"])

        # 2. Genres
        genres = []
        for genre_name in movie_data["genres"]:
            genre = await get_or_create_genre(db, genre_name)
            genres.append(genre)

        # 3. Stars
        stars = []
        for star_name in movie_data["stars"]:
            star = await get_or_create_star(db, star_name)
            stars.append(star)

        # 4. Directors
        directors = []
        for director_name in movie_data["directors"]:
            director = await get_or_create_director(db, director_name)
            directors.append(director)

        # 5. Створюємо Movie
        movie = MovieModel(
            name=movie_data["name"],
            year=movie_data["year"],
            time=movie_data["time"],
            imdb=movie_data["imdb"],
            votes=movie_data["votes"],
            meta_score=movie_data.get("meta_score"),  # може бути None
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
    print(f"\n✅ Успішно додано {len(movies_data)} фільмів!")


# ========================================================================
# MAIN
# ========================================================================


async def main():
    """ """
    print("=" * 60)
    print("🎬 DATABASE SEEDER")
    print("=" * 60)

    json_file = Path(__file__).parent / "movies_seed_data.json"

    if not json_file.exists():
        print(f"❌ Файл {json_file} не знайдено!")
        print("Створи його або вкажи правильний шлях.")
        return

    print(f"📂 Читаємо дані з: {json_file}")
    with open(json_file, "r", encoding="utf-8") as f:
        movies_data = json.load(f)

    print(f"✅ Завантажено {len(movies_data)} фільмів з JSON")

    # Підключаємось до БД
    async with AsyncSessionLocal() as db:
        # Опціонально: очистити БД перед seed
        # await clear_database(db, confirm=True)  # ← розкоментуй для очищення!

        # Додаємо фільми
        await seed_movies(db, movies_data)

    print("\n" + "=" * 60)
    print("🎉 SEEDING ЗАВЕРШЕНО!")
    print("=" * 60)
    print("\n💡 Тепер можеш перевірити:")
    print("   - SELECT COUNT(*) FROM movies;")
    print("   - GET /api/v1/movies")
    print()


if __name__ == "__main__":
    asyncio.run(main())
