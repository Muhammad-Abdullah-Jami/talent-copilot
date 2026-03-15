# routers/confirm.py
# Handles HITL yes/no confirmations — NOW with real job execution

import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.confirm import ConfirmRequest, ConfirmResponse
from backend.models.confirmation import Confirmation
from backend.models.candidate import Candidate
from backend.models.job import Job
from backend.services.memory import save_message
from backend.services.job_manager import start_ingestion_job
from backend.services.tenant_manager import ensure_tenant_user_session


router = APIRouter(prefix="/confirm", tags=["Confirmation"])


@router.post("", response_model=ConfirmResponse)
async def confirm(request: ConfirmRequest, db: Session = Depends(get_db)):
    """
    Process a HITL confirmation.
    Now actually executes tools when approved.
    """
    ensure_tenant_user_session(db, request.tenant_id, request.user_id, request.session_id)
    # Find the confirmation — must be pending AND belong to this tenant/session
    confirmation = db.query(Confirmation).filter(
        Confirmation.id == request.confirmation_id,
        Confirmation.tenant_id == request.tenant_id,
        Confirmation.session_id == request.session_id,
        Confirmation.status == "pending"
    ).first()

    if not confirmation:
        raise HTTPException(
            status_code=404,
            detail="Confirmation not found or already resolved"
        )

    if request.decision.lower() == "yes":
        # APPROVED
        confirmation.status = "approved"
        confirmation.resolved_at = datetime.utcnow()

        if confirmation.tool_name == "cv_save":
            payload = json.loads(confirmation.tool_payload)
            candidate_data = payload.get("candidate_data", {})

            if isinstance(candidate_data, str):
                try:
                    candidate_data = json.loads(candidate_data)
                except json.JSONDecodeError:
                    candidate_data = {}

            candidate = Candidate(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                session_id=request.session_id,
                name=candidate_data.get("name", "Unknown"),
                email=candidate_data.get("email"),
                phone=candidate_data.get("phone"),
                skills=json.dumps(candidate_data.get("skills", [])),
                experience=json.dumps(candidate_data.get("experience", [])),
                education=json.dumps(candidate_data.get("education", [])),
                projects=json.dumps(candidate_data.get("projects", [])),
                raw_text=candidate_data.get("raw_text", "")
            )
            db.add(candidate)
            db.commit()

            save_message(
                db, request.session_id, request.tenant_id,
                "assistant", "Candidate profile saved to workspace."
            )

            return ConfirmResponse(
                message="Candidate profile saved to workspace."
            )

        elif confirmation.tool_name == "github_ingest":
            payload = json.loads(confirmation.tool_payload)

            job = Job(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                job_type="github_ingest",
                status="queued",
                payload=confirmation.tool_payload
            )
            db.add(job)
            db.commit()

            # START THE BACKGROUND JOB — this is the new part
            start_ingestion_job(job.id, request.tenant_id, request.user_id)

            save_message(
                db, request.session_id, request.tenant_id,
                "assistant",
                f"GitHub ingestion job started for {payload.get('repo_url', '')}. Job ID: {job.id}"
            )

            return ConfirmResponse(
                message=f"Ingestion job started. Job ID: {job.id}",
                job_id=job.id
            )

    else:
        # DENIED
        confirmation.status = "denied"
        confirmation.resolved_at = datetime.utcnow()
        db.commit()

        save_message(
            db, request.session_id, request.tenant_id,
            "assistant", "Action cancelled. How else can I help?"
        )

        return ConfirmResponse(
            message="Action cancelled. How else can I help?"
        )