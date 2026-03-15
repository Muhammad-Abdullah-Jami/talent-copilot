# routers/workspace.py
# Returns real workspace data from the database

import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.workspace import (
    WorkspaceResponse, CandidateSnapshot, RepoSnapshot
)
from backend.models.candidate import Candidate
from backend.models.repository import Repository
from backend.services.memory import get_session_summary

router = APIRouter(prefix="/workspace", tags=["Workspace"])


@router.get("", response_model=WorkspaceResponse)
async def get_workspace(
    tenant_id: str = Query(...),
    user_id: str = Query(...),
    session_id: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get workspace snapshot — all candidates and repos for this tenant/user.
    Enforces tenant isolation: you only see YOUR data.
    """
    # Get candidates for this tenant/user
    candidates = db.query(Candidate).filter(
        Candidate.tenant_id == tenant_id,
        Candidate.user_id == user_id
    ).all()

    candidate_list = [
        CandidateSnapshot(
            id=c.id,
            name=c.name,
            email=c.email,
            skills=c.skills
        ) for c in candidates
    ]

    # Get repos for this tenant/user
    repos = db.query(Repository).filter(
        Repository.tenant_id == tenant_id,
        Repository.user_id == user_id
    ).all()

    repo_list = [
        RepoSnapshot(
            id=r.id,
            repo_url=r.repo_url,
            repo_name=r.repo_name
        ) for r in repos
    ]

    # Get session summary if session_id provided
    summary = None
    if session_id:
        summary = get_session_summary(db, session_id, tenant_id)

    return WorkspaceResponse(
        tenant_id=tenant_id,
        user_id=user_id,
        candidates=candidate_list,
        repositories=repo_list,
        session_summary=summary
    )