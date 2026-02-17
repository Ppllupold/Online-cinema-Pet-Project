from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.accounts import UserModel
from src.database.models.movies import (
    MovieModel,
)


async def toggle_favorite(db: AsyncSession, user: UserModel, movie_id: int):
    movie: MovieModel | None = await db.get(MovieModel, movie_id)

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    if movie in user.favorite_movies:
        user.favorite_movies.remove(movie)
        await db.commit()
        return {"status": "removed", "is_favorite": False}
    else:
        user.favorite_movies.append(movie)
        await db.commit()
        return {"status": "added", "is_favorite": True}
