# schemas/job.py
# For job status tracking

from pydantic import BaseModel
from typing import Optional


class JobStatusResponse(BaseModel):
    """Current status of a background job"""
    job_id: str
    job_type: str
    status: str  # queued / running / succeeded / failed
    result: Optional[dict] = None
    error: Optional[str] = None