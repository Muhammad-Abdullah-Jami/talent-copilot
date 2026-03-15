# models/session_summary.py
# Stores summarized versions of older messages
# When conversation gets long, we summarize old messages to save context window space
# This is the "memory windowing" the task requires

import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # The LLM-generated summary of older messages
    summary = Column(Text, nullable=False)
    
    # How many messages were summarized (so we know which ones to skip)
    messages_summarized_up_to = Column(Integer, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())