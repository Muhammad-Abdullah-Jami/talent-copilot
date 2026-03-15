# models/job.py
# Tracks background jobs (like GitHub repo ingestion)
# Status flow: queued → running → succeeded/failed
# This makes long operations non-blocking

import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # "github_ingest" etc.
    job_type = Column(String, nullable=False)
    
    # queued / running / succeeded / failed
    status = Column(String, nullable=False, default="queued")
    
    # Input and result stored as JSON strings
    payload = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())