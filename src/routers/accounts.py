from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import accounts as accounts_crud
from src.database.models import UserModel
from src.dependencies.auth import get_current_user
from src.dependencies.db import get_db
from src.schemas.accounts import (
    UserRegisterSchema,
    RenewActivationRequest,
    TokenResponse,
    LoginRequest,
    AccessTokenResponse,
    RefreshTokenRequest,
    PasswordChangeRequest,
    PasswordResetRequestEmail,
    PasswordResetConfirm,
)
from src.services.email import send_activation_email, send_password_reset_email

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Creates a new user account with the provided email and password. "
        "Sends an activation email with a unique token. "
        "The account must be activated before login is possible."
    ),
    responses={
        201: {"description": "Account created successfully, activation email sent"},
        400: {"description": "Email already registered or invalid data"},
    },
)
async def register_account(
    user: UserRegisterSchema, db: AsyncSession = Depends(get_db)
) -> dict:
    user_created = await accounts_crud.create_user(db, user)
    await send_activation_email(user.email, user_created.activation_token.token)
    return {
        "message": "Account created successfully! Check your email to activate your account.",
    }


@router.post(
    "/activate/{activation_token}",
    status_code=status.HTTP_200_OK,
    summary="Activate user account",
    description=(
        "Activates the user account using the token received via email. "
        "The token is a one-time use UUID sent during registration or via the renew-activation-link endpoint."
    ),
    responses={
        200: {"description": "Account activated successfully"},
        400: {"description": "Invalid or expired activation token"},
    },
)
async def activate_account(activation_token: str, db: AsyncSession = Depends(get_db)):
    await accounts_crud.activate_account(db, activation_token)
    return {"message": "Account activated successfully!"}


@router.post(
    "/renew-activation-link",
    status_code=200,
    summary="Resend activation email",
    description=(
        "Generates a new activation token and sends a new activation email to the provided address. "
        "Use this if the original activation email expired or was not received."
    ),
    responses={
        200: {"description": "New activation link sent to email"},
        404: {"description": "Email not found or account already active"},
    },
)
async def renew_activation_link(
    request: RenewActivationRequest, db: AsyncSession = Depends(get_db)
):
    activation_token = await accounts_crud.create_activation_token(db, request.email)
    await db.commit()

    email_sent = await send_activation_email(
        to_email=request.email, activation_token=activation_token.token
    )

    if not email_sent:
        return {
            "message": "New activation link created but email failed. Please contact support.",
            "token": activation_token.token,
        }

    return {"message": "New activation link has been sent to your email."}


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get tokens",
    description=(
        "Authenticates the user with email and password. "
        "Returns a JWT access token (short-lived) and a refresh token (long-lived). "
        "The account must be activated before login."
    ),
    responses={
        200: {"description": "Login successful, tokens returned"},
        401: {"description": "Invalid credentials"},
        403: {"description": "Account not activated"},
    },
)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await accounts_crud.authenticate_user(
        db, credentials.email, credentials.password
    )
    access_token, refresh_token = await accounts_crud.create_tokens_for_user(db, user)
    await db.commit()
    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Refresh access token",
    description=(
        "Issues a new JWT access token using a valid refresh token. "
        "Use this when the access token has expired. "
        "The refresh token itself is not rotated."
    ),
    responses={
        200: {"description": "New access token returned"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    new_access_token = await accounts_crud.refresh_access_token(
        db, request.refresh_token
    )
    return AccessTokenResponse(access_token=new_access_token, token_type="bearer")


@router.post(
    "/logout",
    status_code=204,
    summary="Logout from current device",
    description=(
        "Revokes the provided refresh token, effectively logging out from the current session. "
        "The access token remains valid until expiry."
    ),
    responses={
        204: {"description": "Logged out successfully"},
        401: {"description": "Invalid or already revoked refresh token"},
    },
)
async def logout(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    await accounts_crud.revoke_refresh_token(db, request.refresh_token)
    await db.commit()


@router.post(
    "/logout-all",
    status_code=204,
    summary="Logout from all devices",
    description=(
        "Revokes all active refresh tokens for the currently authenticated user. "
        "Requires a valid access token in the Authorization header."
    ),
    responses={
        204: {"description": "All sessions revoked"},
        401: {"description": "Not authenticated"},
    },
)
async def logout_all_devices(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await accounts_crud.revoke_all_user_tokens(db, current_user.id)
    await db.commit()


@router.get(
    "/me",
    summary="Get current user info",
    description=(
        "Returns basic profile information of the currently authenticated user. "
        "Requires a valid JWT access token in the Authorization header."
    ),
    responses={
        200: {"description": "User info returned"},
        401: {"description": "Not authenticated"},
    },
)
async def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
    }


@router.post(
    "/password/change",
    status_code=200,
    summary="Change password",
    description=(
        "Changes the password for the currently authenticated user. "
        "Requires the current password for verification and a new password. "
        "All active sessions remain valid after the change."
    ),
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Old password is incorrect"},
        401: {"description": "Not authenticated"},
    },
)
async def change_password(
    request: PasswordChangeRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await accounts_crud.change_password(
        db, current_user, request.old_password, request.new_password
    )
    await db.commit()
    return {"message": "Password changed successfully"}


@router.post(
    "/password/reset-request",
    status_code=200,
    summary="Request password reset",
    description=(
        "Sends a password reset email to the provided address if it is registered. "
        "Always returns a success message regardless of whether the email exists, "
        "to prevent user enumeration."
    ),
    responses={
        200: {"description": "Reset email sent if address is registered"},
    },
)
async def request_password_reset(
    request: PasswordResetRequestEmail, db: AsyncSession = Depends(get_db)
):
    reset_token = await accounts_crud.request_password_reset(db, request.email)

    if reset_token:
        await db.commit()
        await send_password_reset_email(to_email=request.email, token=reset_token.token)

    return {
        "message": "If this email is registered, you will receive a password reset link."
    }


@router.post(
    "/password/reset-confirm",
    status_code=200,
    summary="Confirm password reset",
    description=(
        "Resets the user password using the token received via email. "
        "The token is single-use and expires after a set period. "
        "After a successful reset, the user can login with the new password."
    ),
    responses={
        200: {"description": "Password reset successfully"},
        400: {"description": "Invalid or expired reset token"},
    },
)
async def reset_password_confirm(
    request: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
):
    await accounts_crud.reset_password_with_token(
        db, request.token, request.new_password
    )
    return {"message": "Password has been reset successfully. You can now login."}