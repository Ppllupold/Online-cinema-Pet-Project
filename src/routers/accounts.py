from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import accounts as accounts_crud
from src.database.models import UserModel
from src.dependencies.auth import get_current_user
from src.dependencies.db import get_db
from src.schemas.accounts import UserRegisterSchema, RenewActivationRequest, TokenResponse, LoginRequest, \
    AccessTokenResponse, RefreshTokenRequest, PasswordChangeRequest, PasswordResetRequestEmail, PasswordResetConfirm
from src.services.email import send_activation_email, send_password_reset_email

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_account(
    user: UserRegisterSchema, db: AsyncSession = Depends(get_db)
) -> dict:
    user_created = await accounts_crud.create_user(db, user)
    await send_activation_email(user.email, user_created.activation_token.token)
    return {
        "message": "Account created successfully! Check your email to activate your account.",
    }


@router.post("/activate/{activation_token}", status_code=status.HTTP_200_OK)
async def activate_account(activation_token: str, db: AsyncSession = Depends(get_db)):
    user = await accounts_crud.activate_account(db, activation_token)
    return {"message": "Account activated successfully!"}


@router.post("/renew-activation-link", status_code=200)
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
            "token": activation_token.token,  # для debug
        }

    return {"message": "New activation link has been sent to your email."}

@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await accounts_crud.authenticate_user(
        db, credentials.email, credentials.password
    )

    access_token, refresh_token = await accounts_crud.create_tokens_for_user(db, user)

    await db.commit()

    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
):
    new_access_token = await accounts_crud.refresh_access_token(db, request.refresh_token)

    return AccessTokenResponse(access_token=new_access_token, token_type="bearer")


@router.post("/logout", status_code=204)
async def logout(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    await accounts_crud.revoke_refresh_token(db, request.refresh_token)
    await db.commit()


@router.post("/logout-all", status_code=204)
async def logout_all_devices(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await accounts_crud.revoke_all_user_tokens(db, current_user.id)
    await db.commit()


@router.get("/me")
async def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
    }



@router.post("/password/change", status_code=200)
async def change_password(
        request: PasswordChangeRequest,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    await accounts_crud.change_password(
        db,
        current_user,
        request.old_password,
        request.new_password
    )

    await db.commit()

    return {"message": "Password changed successfully"}


@router.post("/password/reset-request", status_code=200)
async def request_password_reset(
        request: PasswordResetRequestEmail,
        db: AsyncSession = Depends(get_db)
):
    reset_token = await accounts_crud.request_password_reset(
        db,
        request.email
    )

    if reset_token:
        await db.commit()

        await send_password_reset_email(
            to_email=request.email,
            token=reset_token.token
        )

    return {
        "message": "If this email is registered, you will receive a password reset link."
    }


@router.post("/password/reset-confirm", status_code=200)
async def reset_password_confirm(
        request: PasswordResetConfirm,
        db: AsyncSession = Depends(get_db)
):
    user = await accounts_crud.reset_password_with_token(
        db,
        request.token,
        request.new_password
    )

    return {"message": "Password has been reset successfully. You can now login."}
