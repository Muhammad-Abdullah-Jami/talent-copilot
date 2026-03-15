# models/message.py
# Stores every chat message (user and assistant)
# This is the core of the memory system

import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # role is "user" or "assistant" — matches LangChain message format
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)  # the actual message text
    
    # sequence number for ordering messages within a session
    sequence = Column(Integer, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())