from pydantic import BaseModel, EmailStr, field_validator
import re

from src.security.passwords import validate_password_strength


class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str

    @classmethod
    @field_validator("password", mode="before")
    def validate_password(cls, password):
        return validate_password_strength(password)

    @classmethod
    @field_validator("email", mode="before")
    def validate_email(cls, email):
        return email.lower().strip()


class RenewActivationRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, password):
        return validate_password_strength(password)


class PasswordResetRequestEmail(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, password):
        return validate_password_strength(password)
