# models/confirmation.py
# Tracks HITL confirmations — the core of the approval system
# Every tool action creates a confirmation record BEFORE executing
# Status goes: pending → approved/denied

import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base


class Confirmation(Base):
    __tablename__ = "confirmations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    
    # What tool needs confirmation: "github_ingest" or "cv_save"
    tool_name = Column(String, nullable=False)
    
    # The payload for the tool (e.g., repo_url or candidate data)
    # Stored as JSON string so we can verify the SAME payload gets executed
    tool_payload = Column(Text, nullable=False)
    
    # pending / approved / denied
    status = Column(String, nullable=False, default="pending")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)