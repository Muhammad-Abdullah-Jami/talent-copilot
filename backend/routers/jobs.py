# routers/jobs.py
# Returns real job status from the database

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.job import JobStatusResponse
from backend.models.job import Job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Get current status of a background job.
    Frontend polls this every few seconds to check progress.
    """
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Parse result JSON if it exists
    result_data = None
    if job.result:
        try:
            result_data = json.loads(job.result)
        except json.JSONDecodeError:
            result_data = {"raw": job.result}

    return JobStatusResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        result=result_data,
        error=job.error
    )