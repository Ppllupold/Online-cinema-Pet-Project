from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import accounts as accounts_crud
from src.dependencies.db import get_db
from src.schemas.accounts import UserRegisterSchema, RenewActivationRequest
from src.services.email import send_activation_email

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
