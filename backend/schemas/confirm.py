#  schemas/confirms.py
# for the HITL yes no confiramtion endpoints

from pydantic import BaseModel

class ConfirmRequest(BaseModel):
    """User's yes/no decision on a pending confirmation"""
    tenant_id: str
    user_id:str
    session_id: str
    confirmation_id: str
    decision: str # yes or no

class ConfirmResponse(BaseModel):
    """Result after processing the confrmation"""
    message: str
    job_id: str = None #if yes on github_ingest, a job is created
    