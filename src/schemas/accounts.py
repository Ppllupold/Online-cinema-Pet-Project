from pydantic import BaseModel, EmailStr, field_validator
import re


class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str

    @classmethod
    @field_validator("password", mode="before")
    def validate_password(cls, password):
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters.")
        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lower letter.")
        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[@$!%*?&#]", password):
            raise ValueError(
                "Password must contain at least one special character: @, $, !, %, *, ?, #, &."
            )
        return password

    @classmethod
    @field_validator("email", mode="before")
    def validate_email(cls, email):
        return email.lower().strip()


class RenewActivationRequest(BaseModel):
    email: EmailStr