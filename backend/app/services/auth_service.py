"""
LiRA Backend — Auth Service
Business logic for registration, login, Google OAuth.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, LiRAException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.oauth_account import OAuthAccount
from app.models.user import User


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        email: str,
        password: str,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> User:
        # Check email uniqueness
        result = await self.db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ConflictError("A user with this email already exists")

        # Check username uniqueness
        if username:
            result = await self.db.execute(select(User).where(User.username == username))
            if result.scalar_one_or_none():
                raise ConflictError("This username is already taken")

        user = User(
            email=email,
            password_hash=hash_password(password),
            username=username,
            full_name=full_name,
            is_verified=False,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, email: str, password: str) -> Tuple[User, str, str]:
        """Returns (user, access_token, refresh_token)."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            raise LiRAException("Invalid email or password", status_code=401)

        if not verify_password(password, user.password_hash):
            raise LiRAException("Invalid email or password", status_code=401)

        if not user.is_active:
            raise LiRAException("Account is disabled", status_code=403)

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        return user, access_token, refresh_token

    async def refresh_tokens(self, refresh_token: str) -> Tuple[str, str]:
        """Validate refresh token and issue new token pair."""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise LiRAException("Invalid refresh token", status_code=401)

        user_id = payload.get("sub")
        if not user_id:
            raise LiRAException("Invalid refresh token", status_code=401)

        result = await self.db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise LiRAException("User not found or inactive", status_code=401)

        new_access = create_access_token(str(user.id))
        new_refresh = create_refresh_token(str(user.id))
        return new_access, new_refresh

    async def get_or_create_google_user(
        self,
        google_id: str,
        email: str,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """Find user by Google account or create new one. Returns (user, access, refresh)."""

        # Check if Google account already linked
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == "google",
                OAuthAccount.provider_account_id == google_id,
            )
        )
        oauth = result.scalar_one_or_none()

        if oauth:
            # Existing user — load and login
            result = await self.db.execute(select(User).where(User.id == oauth.user_id))
            user = result.scalar_one_or_none()
            if not user or not user.is_active:
                raise LiRAException("User account is disabled", status_code=403)

            user.last_login_at = datetime.now(timezone.utc)
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            await self.db.commit()
        else:
            # Check if email already exists (link OAuth to existing account)
            result = await self.db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if user:
                # Link Google account to existing user
                oauth_account = OAuthAccount(
                    user_id=user.id,
                    provider="google",
                    provider_account_id=google_id,
                    provider_email=email,
                )
                self.db.add(oauth_account)
                user.is_verified = True
                user.last_login_at = datetime.now(timezone.utc)
                if avatar_url and not user.avatar_url:
                    user.avatar_url = avatar_url
                await self.db.commit()
            else:
                # Create new user + OAuth account
                user = User(
                    email=email,
                    full_name=full_name,
                    avatar_url=avatar_url,
                    is_verified=True,  # Google-verified email
                )
                self.db.add(user)
                await self.db.flush()  # get user.id

                oauth_account = OAuthAccount(
                    user_id=user.id,
                    provider="google",
                    provider_account_id=google_id,
                    provider_email=email,
                )
                self.db.add(oauth_account)
                user.last_login_at = datetime.now(timezone.utc)
                await self.db.commit()
                await self.db.refresh(user)

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        return user, access_token, refresh_token
