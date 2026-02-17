from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import stars as stars_crud
from src.config.dependencies import get_db
from src.schemas.stars import (
    StarCreate,
    StarUpdate,
    StarListResponse,
    StarDetailResponse,
)

router = APIRouter(prefix="/stars", tags=["Stars"])


@router.get("/", response_model=list[StarListResponse])
async def get_stars(db: AsyncSession = Depends(get_db)):
    stars = await stars_crud.get_all_stars(db)
    return [StarListResponse.model_validate(star) for star in stars]


@router.get("/{star_id}", response_model=StarDetailResponse)
async def get_star(star_id: int, db: AsyncSession = Depends(get_db)):
    star = await stars_crud.get_star_by_id(db, star_id)
    return StarDetailResponse.model_validate(star)


@router.post("/", response_model=StarDetailResponse, status_code=201)
async def create_star(
    schema: StarCreate,
    db: AsyncSession = Depends(get_db)
):
    star = await stars_crud.create_star(db, schema)
    await db.commit()
    return StarDetailResponse.model_validate(star)


@router.patch("/{star_id}", response_model=StarDetailResponse)
async def update_star(
    star_id: int,
    schema: StarUpdate,
    db: AsyncSession = Depends(get_db)
):
    star = await stars_crud.update_star(db, star_id, schema)
    await db.commit()
    return StarDetailResponse.model_validate(star)


@router.delete("/{star_id}", status_code=204)
async def delete_star(star_id: int, db: AsyncSession = Depends(get_db)):
    await stars_crud.delete_star(db, star_id)
    await db.commit()