from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.movies import Star
from src.schemas.stars import StarCreate, StarUpdate


async def get_all_stars(db: AsyncSession) -> list[Star]:
    result = await db.scalars(select(Star).order_by(Star.name))
    return list(result.all())


async def get_star_by_id(db: AsyncSession, star_id: int) -> Star:
    star = await db.get(Star, star_id)
    if not star:
        raise HTTPException(status_code=404, detail="Star not found")
    return star


async def create_star(db: AsyncSession, schema: StarCreate) -> Star:
    existing = await db.scalar(
        select(Star).where(func.lower(Star.name) == schema.name.lower())
    )
    if existing:
        raise HTTPException(status_code=409, detail="Star already exists")

    star = Star(name=schema.name)
    db.add(star)
    await db.flush()
    await db.refresh(star)
    return star


async def update_star(db: AsyncSession, star_id: int, schema: StarUpdate) -> Star:
    star = await get_star_by_id(db, star_id)

    update_data = schema.model_dump(exclude_unset=True)

    if "name" in update_data:
        existing = await db.scalar(
            select(Star).where(
                func.lower(Star.name) == update_data["name"].lower(), Star.id != star_id
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Star already exists")

    for field, value in update_data.items():
        setattr(star, field, value)

    await db.flush()
    await db.refresh(star)
    return star


async def delete_star(db: AsyncSession, star_id: int) -> None:
    star = await get_star_by_id(db, star_id)
    await db.delete(star)
    await db.flush()
