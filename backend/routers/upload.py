# routers/upload.py
# Handles CV file upload, parsing, and HITL confirmation creation

import json
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.upload import CVUploadResponse
from backend.services.cv_parser import parse_cv
from backend.models.confirmation import Confirmation
from backend.services.memory import save_message
from backend.services.tenant_manager import ensure_tenant_user_session


router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/cv", response_model=CVUploadResponse)
async def upload_cv(
    tenant_id: str = Form(...),
    user_id: str = Form(...),
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a CV.
    
    Flow:
    1. Read file bytes
    2. Parse CV (extract text + LLM structuring)
    3. Create HITL confirmation for saving
    4. Return parsed data + confirmation_id
    
    The CV is NOT saved to workspace yet — user must approve first.
    """
    ensure_tenant_user_session(db, tenant_id, user_id, session_id)
    # Validate file type
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported."
        )

    # Read file bytes
    file_bytes = await file.read()

    # Parse the CV
    try:
        parsed_data = await parse_cv(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create HITL confirmation — user must approve saving
    confirmation = Confirmation(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        tool_name="cv_save",
        tool_payload=json.dumps({"candidate_data": parsed_data}),
        status="pending"
    )
    db.add(confirmation)
    db.commit()

    # Save a message about the parsing
    save_message(
        db, session_id, tenant_id,
        "assistant",
        f"CV parsed for {parsed_data.get('name', 'Unknown')}. "
        f"Do you want me to save this candidate profile to the workspace? (yes/no)"
    )

    return CVUploadResponse(
        message=f"CV parsed successfully for {parsed_data.get('name', 'Unknown')}.",
        parsed_data=parsed_data,
        confirmation_id=confirmation.id
    )