"""Request and response models for authentication endpoints."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Credentials submitted by the login page."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthUser(BaseModel):
    """Safe subset of the Supabase user returned to the frontend."""

    id: str
    email: Optional[EmailStr] = None


class LoginResponse(BaseModel):
    """Session tokens and user identity returned after a successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    expires_at: Optional[int] = None
    user: AuthUser

