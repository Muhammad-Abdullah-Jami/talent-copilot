# models/tenant.py
# Represents a tenant (company/team) in the multi-tenant system
# Each tenant's data is completely isolated from others

import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from backend.database import Base


class Tenant(Base):
    # __tablename__ tells SQLAlchemy what to name the table in PostgreSQL
    __tablename__ = "tenants"

    # Column() defines a column in the table
    # String = VARCHAR, DateTime = TIMESTAMP
    # primary_key=True means this is the unique identifier
    # default= runs automatically when creating a new row
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # nullable=False = required field
    created_at = Column(DateTime(timezone=True), server_default=func.now())