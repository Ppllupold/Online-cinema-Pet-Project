from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import UserModel, RefreshTokenModel, PasswordResetTokenModel
from sqlalchemy import select

from src.services.jwt import jwt_manager

REGISTER_URL = "/api/v1/accounts/register"
STRONG_PASSWORD = "8f6@E6hR~<T1w"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_user_register(client: AsyncClient, db_session: AsyncSession):
    with patch(
        "src.routers.accounts.send_activation_email", new_callable=AsyncMock
    ) as mock_email:
        mock_email.return_value = True
        response = await client.post(
            REGISTER_URL,
            json={"email": "test@gmail.com", "password": f"{STRONG_PASSWORD}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == {
            "message": "Account created successfully! Check your email to activate your account.",
        }
        new_user = await db_session.get(UserModel, 1)

        assert new_user.is_active is False
        await db_session.refresh(new_user, ["activation_token"])
        mock_email.assert_called_once_with(
            new_user.email, new_user.activation_token.token
        )


@pytest.mark.asyncio
async def test_user_register_duplicate_email(
    client: AsyncClient, db_session: AsyncSession
):
    with patch(
        "src.routers.accounts.send_activation_email", new_callable=AsyncMock
    ) as mock_email:
        mock_email.return_value = True
        await client.post(
            REGISTER_URL,
            json={"email": "test@gmail.com", "password": f"{STRONG_PASSWORD}"},
        )
        response = await client.post(
            REGISTER_URL,
            json={"email": "test@gmail.com", "password": f"{STRONG_PASSWORD}"},
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json() == {"detail": "User with this email already exists"}


@pytest.mark.asyncio
async def test_user_activate_account_success(
    client: AsyncClient, db_session: AsyncSession, register_user: UserModel
):
    response = await client.post(
        f"/api/v1/accounts/activate/{register_user.activation_token.token}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Account activated successfully!"}
    await db_session.refresh(register_user, ["activation_token"])
    assert register_user.is_active is True
    assert register_user.activation_token is None


@pytest.mark.asyncio
async def test_user_activate_account_no_token(
    client: AsyncClient, db_session: AsyncSession, register_user: UserModel
):
    response = await client.post(f"/api/v1/accounts/activate/invalid")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Invalid activation token"}


@pytest.mark.asyncio
async def test_user_activate_account_token_expired(
    client: AsyncClient, db_session: AsyncSession, register_user: UserModel
):

    register_user.activation_token.expires_at = datetime(
        2021, 11, 11, 11, 11, 11, tzinfo=timezone.utc
    )
    response = await client.post(
        f"/api/v1/accounts/activate/{register_user.activation_token.token}"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Activation token has expired"}


@pytest.mark.asyncio
async def test_user_activate_account_user_activated(
    client: AsyncClient, db_session: AsyncSession, register_user: UserModel
):
    register_user.is_active = True
    response = await client.post(
        f"/api/v1/accounts/activate/{register_user.activation_token.token}"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Account already activated"}


@pytest.mark.asyncio
async def test_renew_activation_link(
    client: AsyncClient, db_session: AsyncSession, register_user: UserModel
):
    with patch(
        "src.routers.accounts.send_activation_email", new_callable=AsyncMock
    ) as mock_email:
        mock_email.return_value = True
        response = await client.post(
            f"/api/v1/accounts/renew-activation-link",
            json={"email": register_user.email},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "message": "New activation link has been sent to your email."
        }
        assert mock_email.call_count == 1


@pytest.mark.asyncio
async def test_login(
    client: AsyncClient, db_session: AsyncSession, register_user: UserModel
):
    register_user.is_active = True
    await db_session.flush()

    response = await client.post(
        f"/api/v1/accounts/login",
        json={"email": register_user.email, "password": f"{STRONG_PASSWORD}"},
    )
    assert response.status_code == status.HTTP_200_OK
    refresh_token = await db_session.scalar(
        select(RefreshTokenModel).where(RefreshTokenModel.user_id == register_user.id)
    )
    data = response.json()
    assert data["access_token"] is not None
    assert len(data["access_token"]) > 0
    assert data["refresh_token"] == refresh_token.token
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh(
    client: AsyncClient, db_session: AsyncSession, active_user: UserModel
):
    refresh = await db_session.scalar(
        select(RefreshTokenModel).where(RefreshTokenModel.user_id == active_user.id)
    )
    response = await client.post(
        f"/api/v1/accounts/refresh", json={"refresh_token": refresh.token}
    )
    data = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert data["access_token"] is not None
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
async def test_logout(
    client: AsyncClient, db_session: AsyncSession, active_user: UserModel
):
    refresh = await db_session.scalar(
        select(RefreshTokenModel).where(RefreshTokenModel.user_id == active_user.id)
    )
    response = await client.post(
        f"/api/v1/accounts/logout", json={"refresh_token": refresh.token}
    )
    await db_session.refresh(active_user, ["refresh_tokens"])
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert active_user.refresh_tokens == []


@pytest.mark.asyncio
async def test_logout_all(
    auth_client: AsyncClient, db_session: AsyncSession, active_user: UserModel
):
    db_session.add(RefreshTokenModel(user_id=active_user.id))
    await db_session.flush()
    response = await auth_client.post(f"/api/v1/accounts/logout-all")
    await db_session.refresh(active_user, ["refresh_tokens"])
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert active_user.refresh_tokens == []


@pytest.mark.asyncio
async def test_password_change(
    auth_client: AsyncClient, db_session: AsyncSession, active_user: UserModel
):
    response = await auth_client.post(
        f"/api/v1/accounts/password/change",
        json={
            "old_password": f"{STRONG_PASSWORD}",
            "new_password": f"{STRONG_PASSWORD}stronger",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Password changed successfully"}
    assert active_user.verify_password(STRONG_PASSWORD) is False


@pytest.mark.asyncio
async def test_password_reset_request(
    auth_client: AsyncClient, db_session: AsyncSession, active_user: UserModel
):
    with patch(
        "src.routers.accounts.send_password_reset_email", new_callable=AsyncMock
    ) as mock_email:
        mock_email.return_value = True
        response = await auth_client.post(
            f"/api/v1/accounts/password/reset-request",
            json={"email": active_user.email},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "message": "If this email is registered, you will receive a password reset link."
        }
        await db_session.refresh(active_user, ["password_reset_token"])
        assert active_user.password_reset_token is not None
        assert mock_email.call_count == 1


@pytest.mark.asyncio
async def test_password_reset_confirm(
    auth_client: AsyncClient, db_session: AsyncSession, active_user: UserModel
):
    password_reset_token = PasswordResetTokenModel(user_id=active_user.id)
    db_session.add(password_reset_token)
    await db_session.flush()
    response = await auth_client.post(
        f"/api/v1/accounts/password/reset-confirm",
        json={
            "token": password_reset_token.token,
            "new_password": f"{STRONG_PASSWORD}stronger",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "message": "Password has been reset successfully. You can now login."
    }
    await db_session.refresh(active_user, ["password_reset_token"])
    assert active_user.password_reset_token is None
    assert active_user.verify_password(f"{STRONG_PASSWORD}stronger") is True
