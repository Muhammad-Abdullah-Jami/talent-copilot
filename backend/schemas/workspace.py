# schemas/workspace.py
# For the workspace snapshot endpoint

from pydantic import BaseModel
from typing import List, Optional


class CandidateSnapshot(BaseModel):
    """Summary of a saved candidate"""
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    skills: Optional[str] = None


class RepoSnapshot(BaseModel):
    """Summary of an ingested repo"""
    id: str
    repo_url: str
    repo_name: Optional[str] = None


class WorkspaceResponse(BaseModel):
    """Everything in the current tenant/user workspace"""
    tenant_id: str
    user_id: str
    candidates: List[CandidateSnapshot] = []
    repositories: List[RepoSnapshot] = []
    session_summary: Optional[str] = None