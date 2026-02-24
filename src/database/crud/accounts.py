# src/crud/users.py
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models.accounts import UserModel, ActivationTokenModel
from src.schemas.accounts import UserRegisterSchema

USER_GROUPE_ID = 1


async def create_user(
    db: AsyncSession,
    schema: UserRegisterSchema,
    group_id: int = USER_GROUPE_ID,
) -> UserModel:
    """
    Create a new user via registration

    Args:
        db: Database session
        schema: User registration data
        group_id: User group (default: 1 = USER)

    Returns:
        Created user with activation token

    Raises:
        HTTPException 409: Email already registered
    """

    existing_user = await db.scalar(
        select(UserModel).where(func.lower(UserModel.email) == schema.email.lower())
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user = UserModel.create(
        email=schema.email.lower(),
        raw_password=schema.password,
        group_id=group_id,
    )

    db.add(user)
    await db.flush()

    activation_token = ActivationTokenModel(user_id=user.id)
    db.add(activation_token)

    await db.flush()
    await db.refresh(user)

    return user


async def activate_account(db: AsyncSession, activation_token: str) -> UserModel:
    token_obj = await db.scalar(
        select(ActivationTokenModel).where(
            ActivationTokenModel.token == activation_token
        )
    )
    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid activation token"
        )

    if token_obj.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activation token has expired",
        )

    user = await db.get(UserModel, token_obj.user_id)

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account already activated"
        )

    user.is_active = True

    await db.delete(token_obj)

    await db.flush()
    await db.refresh(user)

    return user


async def create_activation_token(
        db: AsyncSession,
        email: str
) -> ActivationTokenModel:


    user = await db.scalar(
        select(UserModel).where(
            func.lower(UserModel.email) == email.lower()
        )
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found"
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already activated"
        )

    await db.refresh(user, ["activation_token"])

    if user.activation_token:
        await db.delete(user.activation_token)
        await db.flush()

    token = ActivationTokenModel(user_id=user.id)
    db.add(token)
    await db.flush()
    await db.refresh(token)

    return token