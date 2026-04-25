"""
LiRA Backend — Artifact API Routes
List, download, and preview generated artifacts.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.artifact import Artifact
from app.models.research_history import ResearchHistory
from app.models.user import User
from app.schemas.artifact import ArtifactListResponse, ArtifactResponse

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])


@router.get("/{research_id}", response_model=ArtifactListResponse)
async def list_artifacts(
    research_id: UUID,
    file_type: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all artifacts for a research project."""
    # Verify ownership
    result = await db.execute(
        select(ResearchHistory).where(
            ResearchHistory.id == research_id,
            ResearchHistory.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Research")

    query = select(Artifact).where(Artifact.research_id == research_id)
    if file_type:
        query = query.where(Artifact.file_type == file_type)
    query = query.order_by(Artifact.created_at)

    result = await db.execute(query)
    artifacts = result.scalars().all()

    return ArtifactListResponse(
        items=[ArtifactResponse.model_validate(a) for a in artifacts],
        total=len(artifacts),
    )


@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download an artifact file."""
    result = await db.execute(
        select(Artifact)
        .join(ResearchHistory)
        .where(
            Artifact.id == artifact_id,
            ResearchHistory.user_id == current_user.id,
        )
    )
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise NotFoundError("Artifact")

    return FileResponse(
        path=artifact.storage_path,
        filename=artifact.filename,
        media_type=artifact.mime_type,
    )


@router.get("/{artifact_id}/preview")
async def preview_artifact(
    artifact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview artifact content inline (JSON, CSV text, or image URL)."""
    result = await db.execute(
        select(Artifact)
        .join(ResearchHistory)
        .where(
            Artifact.id == artifact_id,
            ResearchHistory.user_id == current_user.id,
        )
    )
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise NotFoundError("Artifact")

    # For images, return the download URL
    if artifact.file_type in ("png", "jpg", "jpeg", "gif"):
        return {
            "type": "image",
            "url": f"/api/v1/artifacts/{artifact_id}/download",
            "filename": artifact.filename,
        }

    # For text-based files, return content directly
    try:
        import os
        if not os.path.exists(artifact.storage_path):
            raise NotFoundError("Artifact file not found on disk")

        max_preview_size = 500_000  # 500KB preview limit
        file_size = os.path.getsize(artifact.storage_path)

        with open(artifact.storage_path, "r", encoding="utf-8") as f:
            if file_size > max_preview_size:
                content = f.read(max_preview_size)
                truncated = True
            else:
                content = f.read()
                truncated = False

        return {
            "type": artifact.file_type,
            "content": content,
            "filename": artifact.filename,
            "file_size": file_size,
            "truncated": truncated,
        }
    except UnicodeDecodeError:
        return {
            "type": "binary",
            "url": f"/api/v1/artifacts/{artifact_id}/download",
            "filename": artifact.filename,
        }


@router.get("/{research_id}/by-name/{filename}")
async def download_artifact_by_name(
    research_id: UUID,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download an artifact by its filename (most recent match)."""
    from sqlalchemy import desc

    # Verify ownership
    result = await db.execute(
        select(ResearchHistory).where(
            ResearchHistory.id == research_id,
            ResearchHistory.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundError("Research")

    result = await db.execute(
        select(Artifact)
        .where(
            Artifact.research_id == research_id,
            Artifact.filename == filename,
        )
        .order_by(desc(Artifact.created_at))
        .limit(1)
    )
    artifact = result.scalar_one_or_none()

    if not artifact:
        # Fallback: search for the file in the work directory
        import os
        from app.core.config import get_settings
        from pathlib import Path

        settings = get_settings()
        research_dir = Path(settings.STORAGE_LOCAL_ROOT) / str(research_id)

        # Determine MIME type
        mime_map = {
            ".csv": "text/csv",
            ".json": "application/json",
            ".md": "text/markdown",
            ".ris": "application/x-research-info-systems",
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".txt": "text/plain",
        }
        ext = Path(filename).suffix.lower()
        mime_type = mime_map.get(ext, "application/octet-stream")

        # Search recursively in all run directories (newest first)
        if research_dir.exists():
            for run_dir in sorted(research_dir.glob("run-*"), reverse=True):
                # Recursive search within each run directory
                for found_file in run_dir.rglob(filename):
                    if found_file.is_file():
                        return FileResponse(
                            path=str(found_file),
                            filename=filename,
                            media_type=mime_type,
                        )

        # Final fallback: search the project root directory
        # (files may have been generated by standalone pipeline runs)
        project_root = Path(settings.STORAGE_LOCAL_ROOT).resolve().parent
        # Try common locations relative to the backend
        for search_root in [project_root, project_root.parent]:
            candidate = search_root / filename
            if candidate.is_file():
                return FileResponse(
                    path=str(candidate),
                    filename=filename,
                    media_type=mime_type,
                )

        raise NotFoundError("Artifact")

    return FileResponse(
        path=artifact.storage_path,
        filename=artifact.filename,
        media_type=artifact.mime_type,
    )
