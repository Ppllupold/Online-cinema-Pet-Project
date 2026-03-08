from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.database.models.accounts import (
    UserModel,
    ActivationTokenModel,
    RefreshTokenModel,
    PasswordResetTokenModel,
)
from src.schemas.accounts import UserRegisterSchema
from src.services.jwt import jwt_manager

settings = get_settings()

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
    await db.refresh(user, ["activation_token"])

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


async def create_activation_token(db: AsyncSession, email: str) -> ActivationTokenModel:

    user = await db.scalar(
        select(UserModel).where(func.lower(UserModel.email) == email.lower())
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found",
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account already activated"
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


async def authenticate_user(db: AsyncSession, email: str, password: str) -> UserModel:

    user = await db.scalar(
        select(UserModel).where(func.lower(UserModel.email) == email.lower())
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.verify_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not activated. Please check your email.",
        )

    return user


async def create_tokens_for_user(db: AsyncSession, user: UserModel) -> tuple[str, str]:

    access_token = jwt_manager.create_access_token(user_id=user.id)
    refresh_token = jwt_manager.create_refresh_token(user_id=user.id)

    refresh_token_model = RefreshTokenModel.create(
        user_id=user.id,
        days_valid=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
        token=refresh_token,
    )
    db.add(refresh_token_model)
    await db.flush()

    return access_token, refresh_token


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> str:
    try:
        user_id = jwt_manager.verify_refresh_token(refresh_token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_in_db = await db.scalar(
        select(RefreshTokenModel).where(RefreshTokenModel.token == refresh_token)
    )

    if not token_in_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await db.get(UserModel, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active",
        )

    new_access_token = jwt_manager.create_access_token(user_id=user.id)

    return new_access_token


async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> None:

    token_in_db = await db.scalar(
        select(RefreshTokenModel).where(RefreshTokenModel.token == refresh_token)
    )

    if token_in_db:
        await db.delete(token_in_db)
        await db.flush()


async def revoke_all_user_tokens(db: AsyncSession, user_id: int) -> None:
    tokens = await db.scalars(
        select(RefreshTokenModel).where(RefreshTokenModel.user_id == user_id)
    )

    for token in tokens:
        await db.delete(token)

    await db.flush()


async def change_password(
    db: AsyncSession, user: UserModel, old_password: str, new_password: str
) -> None:

    if not user.verify_password(old_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect old password"
        )

    if old_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from old password",
        )

    user.password = new_password

    await db.flush()


async def request_password_reset(
    db: AsyncSession, email: str
) -> PasswordResetTokenModel | None:

    user = await db.scalar(
        select(UserModel).where(func.lower(UserModel.email) == email.lower())
    )

    if not user or not user.is_active:
        return None

    await db.refresh(user, ["password_reset_token"])

    if user.password_reset_token:
        await db.delete(user.password_reset_token)
        await db.flush()

    reset_token = PasswordResetTokenModel(user_id=user.id)
    db.add(reset_token)
    await db.flush()
    await db.refresh(reset_token)

    return reset_token


async def reset_password_with_token(
    db: AsyncSession, token: str, new_password: str
) -> UserModel:

    reset_token = await db.scalar(
        select(PasswordResetTokenModel).where(PasswordResetTokenModel.token == token)
    )

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid password reset token"
        )

    if reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired",
        )

    user: UserModel | None = await db.get(UserModel, reset_token.user_id)

    if not user:
        raise HTTPException(404, "User not found")

    user.password = new_password

    await db.delete(reset_token)

    await db.flush()
    await db.refresh(user)

    return user
