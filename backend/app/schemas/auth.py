"""
LiRA Backend — Auth API Schemas
Request/response models for authentication endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Requests ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = None


# ── Responses ────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: Optional[str]
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    model_config = {"from_attributes": True}


class GoogleOAuthStartResponse(BaseModel):
    authorization_url: str
