# models/user.py
# Represents a user within a tenant
# ForeignKey links this table to the tenants table

import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # ForeignKey = this column MUST match an id in the tenants table
    # This is how we link users to tenants
    # ondelete="CASCADE" = if tenant is deleted, delete all their users too
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())