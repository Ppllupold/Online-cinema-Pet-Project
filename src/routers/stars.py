from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import stars as stars_crud
from src.dependencies.db import get_db
from src.schemas.stars import (
    StarCreate,
    StarUpdate,
    StarListResponse,
    StarDetailResponse,
)

router = APIRouter(prefix="/stars", tags=["Stars"])


@router.get(
    "/",
    response_model=list[StarListResponse],
    summary="List all actors",
    description="Returns a list of all actors (stars) available in the system.",
    responses={
        200: {"description": "List of actors returned"},
    },
)
async def get_stars(db: AsyncSession = Depends(get_db)):
    stars = await stars_crud.get_all_stars(db)
    return [StarListResponse.model_validate(star) for star in stars]


@router.get(
    "/{star_id}",
    response_model=StarDetailResponse,
    summary="Get actor by ID",
    description="Returns detailed information about a single actor including their filmography.",
    responses={
        200: {"description": "Actor details returned"},
        404: {"description": "Actor not found"},
    },
)
async def get_star(star_id: int, db: AsyncSession = Depends(get_db)):
    star = await stars_crud.get_star_by_id(db, star_id)
    return StarDetailResponse.model_validate(star)


@router.post(
    "/",
    response_model=StarDetailResponse,
    status_code=201,
    summary="Create a new actor",
    description="Creates a new actor entry. The name must be unique.",
    responses={
        201: {"description": "Actor created successfully"},
        400: {"description": "Actor with this name already exists"},
    },
)
async def create_star(schema: StarCreate, db: AsyncSession = Depends(get_db)):
    star = await stars_crud.create_star(db, schema)
    return StarDetailResponse.model_validate(star)


@router.patch(
    "/{star_id}",
    response_model=StarDetailResponse,
    summary="Update an actor",
    description="Partially updates an actor by ID. Only provided fields will be updated.",
    responses={
        200: {"description": "Actor updated successfully"},
        404: {"description": "Actor not found"},
        400: {"description": "Actor with this name already exists"},
    },
)
async def update_star(
    star_id: int, schema: StarUpdate, db: AsyncSession = Depends(get_db)
):
    star = await stars_crud.update_star(db, star_id, schema)
    return StarDetailResponse.model_validate(star)


@router.delete(
    "/{star_id}",
    status_code=204,
    summary="Delete an actor",
    description="Deletes an actor by ID. Their association with movies will also be removed.",
    responses={
        204: {"description": "Actor deleted successfully"},
        404: {"description": "Actor not found"},
    },
)
async def delete_star(star_id: int, db: AsyncSession = Depends(get_db)):
    await stars_crud.delete_star(db, star_id)