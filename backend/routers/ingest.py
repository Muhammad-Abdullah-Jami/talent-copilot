# routers/ingest.py
# Handles GitHub repo ingestion (triggered after HITL approval)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.job import JobStatusResponse
from pydantic import BaseModel

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


class IngestRequest(BaseModel):
    tenant_id: str
    user_id: str
    repo_url: str
    confirmation_id: str  # must have an approved confirmation


@router.post("/github", response_model=JobStatusResponse)
async def ingest_github(request: IngestRequest, db: Session = Depends(get_db)):
    """
    Start GitHub repo ingestion job.
    Only runs if the confirmation was approved.
    Returns a job_id that frontend can poll for status.
    """
    # TODO: Phase 6 — wire to job manager
    return JobStatusResponse(
        job_id="placeholder",
        job_type="github_ingest",
        status="queued"
    )