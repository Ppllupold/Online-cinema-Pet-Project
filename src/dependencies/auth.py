from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from src.dependencies.db import get_db
from src.database.models.accounts import UserModel
from src.database.models.shopping import Cart
from src.config.settings import get_settings

settings = get_settings()
security = HTTPBearer()

SECRET_KEY = "your-secret-key-here"  # TODO: винести в .env
ALGORITHM = "HS256"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserModel:

    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user: UserModel | None = await db.get(UserModel, user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is not active"
        )

    return user


async def get_current_user_cart(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Cart:

    await db.refresh(user, ["cart"])

    if user.cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()
        await db.refresh(cart)
        user.cart = cart

    return user.cart
