"""
LiRA Backend — FastAPI Application Factory
Production-ready app with CORS, exception handlers, and lifespan.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.session import engine

# Import all models so SQLAlchemy knows about them
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    settings = get_settings()

    # Create tables on startup (use Alembic in production)
    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup on shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="LiRA — LLM-Integrated Research Assistant. A production-grade systematic literature review platform.",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    register_exception_handlers(app)

    # Routes
    app.include_router(api_router)

    return app


app = create_app()
