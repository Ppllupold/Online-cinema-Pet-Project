from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.db import get_db
from src.database.models import Cart
from src.dependencies.auth import get_current_user_cart
from src.database.crud import shopping as shopping_crud
from src.schemas.shopping import CartResponse

router = APIRouter(prefix="/cart", tags=["Shopping Cart"])


@router.get(
    "/",
    response_model=CartResponse,
    summary="Get current cart",
    description=(
        "Returns the contents of the currently authenticated user's cart, "
        "including all movies, their prices, and the total amount."
    ),
    responses={
        200: {"description": "Cart contents returned"},
        401: {"description": "Not authenticated"},
    },
)
async def get_cart(
    cart: Cart = Depends(get_current_user_cart), db: AsyncSession = Depends(get_db)
):
    return await shopping_crud.get_cart_items(db, cart)


@router.post(
    "/movies/{movie_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add movie to cart",
    description=(
        "Adds the specified movie to the current user's cart. "
        "The movie must exist and must not already be in the cart. "
        "Movies the user has already purchased cannot be added."
    ),
    responses={
        201: {"description": "Movie added to cart"},
        400: {"description": "Movie already in cart or already purchased"},
        404: {"description": "Movie not found"},
        401: {"description": "Not authenticated"},
    },
)
async def add_movie_to_cart(
    movie_id: int,
    cart: Cart = Depends(get_current_user_cart),
    db: AsyncSession = Depends(get_db),
):
    cart_item = await shopping_crud.add_movie_to_cart(movie_id, db, cart)
    return {"message": "Movie added to cart", "movie_id": cart_item.movie_id}


@router.delete(
    "/movies/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove movie from cart",
    description="Removes the specified movie from the current user's cart.",
    responses={
        204: {"description": "Movie removed from cart"},
        404: {"description": "Movie not in cart"},
        401: {"description": "Not authenticated"},
    },
)
async def remove_movie_from_cart(
    movie_id: int,
    cart: Cart = Depends(get_current_user_cart),
    db: AsyncSession = Depends(get_db),
):
    await shopping_crud.remove_movie_from_cart(movie_id, db, cart)


@router.delete(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear cart",
    description="Removes all movies from the current user's cart.",
    responses={
        204: {"description": "Cart cleared"},
        401: {"description": "Not authenticated"},
    },
)
async def clear_cart(
    cart: Cart = Depends(get_current_user_cart), db: AsyncSession = Depends(get_db)
):
    await shopping_crud.clear_cart(cart, db)