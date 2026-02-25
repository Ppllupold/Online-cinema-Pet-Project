# src/services/jwt.py

from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from jose import JWTError, jwt
from fastapi import HTTPException, status

from src.config.settings import get_settings

settings = get_settings()


class JWTManager:

    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    def create_access_token(self, user_id: int, additional_claims: Dict[str, Any] | None = None) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.access_token_expire_minutes
        )

        payload = {
            "sub": str(user_id),
            "type": "access",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def create_refresh_token(self, user_id: int) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self.refresh_token_expire_days
        )

        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def decode_token(self, token: str, token_type: str | None = None) -> Dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            if token_type and payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return payload

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def get_user_id_from_token(self, token: str) -> int:
        payload = self.decode_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            return int(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID in token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def verify_access_token(self, token: str) -> int:
        payload = self.decode_token(token, token_type="access")
        return int(payload["sub"])

    def verify_refresh_token(self, token: str) -> int:
        payload = self.decode_token(token, token_type="refresh")
        return int(payload["sub"])


jwt_manager = JWTManager()
