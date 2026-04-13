"""
LiRA Backend — Approval API Routes
Human-in-the-loop approval actions (ASReview screening).
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.exceptions import LiRAException, NotFoundError
from app.db.session import get_db
from app.models.approval import Approval
from app.models.artifact import Artifact
from app.models.research_history import ResearchHistory
from app.models.user import User
from app.schemas.artifact import ApprovalResponse

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("/{research_id}", response_model=list[ApprovalResponse])
async def list_approvals(
    research_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List approvals for a research project."""
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
        select(Approval)
        .where(Approval.research_id == research_id)
        .order_by(Approval.requested_at.desc())
    )
    approvals = result.scalars().all()
    return [ApprovalResponse.model_validate(a) for a in approvals]


@router.post("/{approval_id}/upload")
async def upload_approval_file(
    approval_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file for an approval (e.g., ASReview export CSV)."""
    result = await db.execute(
        select(Approval)
        .join(ResearchHistory)
        .where(
            Approval.id == approval_id,
            ResearchHistory.user_id == current_user.id,
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise NotFoundError("Approval")

    if approval.status != "pending":
        raise LiRAException("Approval is not pending", status_code=400)

    # Save uploaded file
    settings = get_settings()
    storage_dir = Path(settings.STORAGE_LOCAL_ROOT) / str(approval.research_id) / "uploads"
    storage_dir.mkdir(parents=True, exist_ok=True)

    file_path = storage_dir / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Create artifact record
    artifact = Artifact(
        research_id=approval.research_id,
        run_id=approval.run_id,
        filename=file.filename,
        file_type=file.filename.rsplit(".", 1)[-1] if "." in file.filename else "unknown",
        mime_type=file.content_type or "application/octet-stream",
        file_size=file_path.stat().st_size,
        storage_path=str(file_path),
        description=f"Uploaded for approval: {approval.approval_type}",
    )
    db.add(artifact)

    # Update approval
    approval.uploaded_file_id = artifact.id
    approval.response_data = {"uploaded_file": file.filename}
    await db.commit()

    return {"artifact_id": str(artifact.id), "filename": file.filename}


@router.post("/{approval_id}/respond", response_model=ApprovalResponse)
async def respond_to_approval(
    approval_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve/respond to a pending approval, resuming the workflow."""
    result = await db.execute(
        select(Approval)
        .join(ResearchHistory)
        .where(
            Approval.id == approval_id,
            ResearchHistory.user_id == current_user.id,
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise NotFoundError("Approval")

    if approval.status != "pending":
        raise LiRAException("Approval is not pending", status_code=400)

    if not approval.uploaded_file_id:
        raise LiRAException("No file uploaded yet. Upload a file first.", status_code=400)

    # Mark as approved
    approval.status = "approved"
    approval.responded_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(approval)

    # Resume workflow with uploaded file path
    result = await db.execute(
        select(ResearchHistory).where(ResearchHistory.id == approval.research_id)
    )
    research = result.scalar_one_or_none()
    if research:
        # Get the uploaded file's storage path for resume
        uploaded_artifact = await db.execute(
            select(Artifact).where(Artifact.id == approval.uploaded_file_id)
        )
        artifact = uploaded_artifact.scalar_one_or_none()
        resume_value = artifact.storage_path if artifact else ""

        from app.services.workflow_service import WorkflowService
        workflow_service = WorkflowService(db)
        await workflow_service.resume_workflow(research, approval, resume_value)

    return approval
