# models/repository.py
# Stores ingested GitHub repo data
# Only created after HITL approval + ingestion job completes

import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    repo_url = Column(String, nullable=False)
    repo_name = Column(String, nullable=True)
    readme_content = Column(Text, nullable=True)
    file_tree = Column(Text, nullable=True)
    languages = Column(Text, nullable=True)
    stack_signals = Column(Text, nullable=True)
    code_snippets = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())