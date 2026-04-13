"""
LiRA Backend — Health Check Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def liveness():
    """Basic liveness check."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness check — verifies database connectivity."""
    checks = {"database": "unknown"}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
    }
