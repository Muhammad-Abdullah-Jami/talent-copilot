# models/__init__.py
# Import all models here so SQLAlchemy knows about them
# When Base.metadata.create_all() runs, it creates tables for ALL imported models

from backend.models.tenant import Tenant
from backend.models.user import User
from backend.models.session import Session
from backend.models.message import Message
from backend.models.session_summary import SessionSummary
from backend.models.candidate import Candidate
from backend.models.repository import Repository
from backend.models.confirmation import Confirmation
from backend.models.job import Job