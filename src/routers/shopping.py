# src/routers/shopping.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.db import get_db
from src.database.models import Cart
from src.dependencies.auth import get_current_user_cart
from src.database.crud import shopping as shopping_crud
from src.schemas.shopping import CartResponse

router = APIRouter(prefix="/cart", tags=["Shopping Cart"])


@router.get("/", response_model=CartResponse)
async def get_cart(
    cart: Cart = Depends(get_current_user_cart), db: AsyncSession = Depends(get_db)
):
    return await shopping_crud.get_cart_items(db, cart)


@router.post("/movies/{movie_id}", status_code=status.HTTP_201_CREATED)
async def add_movie_to_cart(
    movie_id: int,
    cart: Cart = Depends(get_current_user_cart),
    db: AsyncSession = Depends(get_db),
):
    cart_item = await shopping_crud.add_movie_to_cart(movie_id, db, cart)
    return {"message": "Movie added to cart", "movie_id": cart_item.movie_id}


@router.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_movie_from_cart(
    movie_id: int,
    cart: Cart = Depends(get_current_user_cart),
    db: AsyncSession = Depends(get_db),
):
    await shopping_crud.remove_movie_from_cart(movie_id, db, cart)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    cart: Cart = Depends(get_current_user_cart), db: AsyncSession = Depends(get_db)
):
    await shopping_crud.clear_cart(cart, db)
