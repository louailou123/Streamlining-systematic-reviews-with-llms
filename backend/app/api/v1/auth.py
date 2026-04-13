"""
LiRA Backend — Auth API Routes
Register, login, refresh, Google OAuth, profile.
"""

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    GoogleOAuthStartResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory state store for CSRF protection (use Redis in production)
_oauth_states: dict[str, bool] = {}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password."""
    service = AuthService(db)
    user = await service.register(
        email=body.email,
        password=body.password,
        username=body.username,
        full_name=body.full_name,
    )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password. Returns JWT token pair."""
    settings = get_settings()
    service = AuthService(db)
    user, access_token, refresh_token = await service.login(body.email, body.password)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    settings = get_settings()
    service = AuthService(db)
    access_token, new_refresh = await service.refresh_tokens(body.refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """Logout (client-side token discard). Server-side token blocklist is optional for v1."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Google OAuth 2.0 ─────────────────────────────────────────

@router.get("/google/login", response_model=GoogleOAuthStartResponse)
async def google_login():
    """Returns the Google OAuth authorization URL for the frontend to redirect to."""
    settings = get_settings()

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = True

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": settings.GOOGLE_SCOPES,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }

    authorization_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return GoogleOAuthStartResponse(authorization_url=authorization_url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Google OAuth callback. Exchanges code for tokens, fetches user info,
    creates/links account, then redirects to frontend with app tokens.
    """
    settings = get_settings()

    # Verify state
    if state not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    del _oauth_states[state]

    # Exchange code for Google tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            },
        )

    if token_response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange OAuth code: {token_response.text}",
        )

    token_data = token_response.json()
    google_access_token = token_data.get("access_token")

    # Fetch user info from Google
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"},
        )

    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch Google user info")

    userinfo = userinfo_response.json()
    google_id = userinfo.get("id")
    email = userinfo.get("email")
    full_name = userinfo.get("name")
    avatar_url = userinfo.get("picture")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Google did not return required user info")

    # Create or link user
    service = AuthService(db)
    user, access_token, refresh_token = await service.get_or_create_google_user(
        google_id=google_id,
        email=email,
        full_name=full_name,
        avatar_url=avatar_url,
    )

    # Redirect to frontend with tokens in query params
    redirect_url = (
        f"{settings.FRONTEND_URL}/auth/callback"
        f"?access_token={access_token}"
        f"&refresh_token={refresh_token}"
    )

    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": redirect_url},
    )


# ── Profile ──────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile."""
    if body.username is not None:
        current_user.username = body.username
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url

    await db.commit()
    await db.refresh(current_user)
    return current_user
