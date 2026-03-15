# models/candidate.py
# Stores parsed CV/resume data for a candidate
# Only saved after HITL approval

import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    
    # All fields stored as Text because CV data varies wildly
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    skills = Column(Text, nullable=True)        # stored as JSON string
    experience = Column(Text, nullable=True)     # stored as JSON string
    education = Column(Text, nullable=True)      # stored as JSON string
    projects = Column(Text, nullable=True)       # stored as JSON string
    raw_text = Column(Text, nullable=True)       # original extracted text
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())