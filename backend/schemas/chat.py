#schemas/chat.py
#Defines the shape of chat requests and response data
# pydanti validates this atuomatiacly and wrong data is instant 422 error

from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    """What the frontend sends when user types a message"""
    tenant_id: str
    user_id: str
    session_id: str
    message: str

class ChatResponse(BaseModel):
    """What we send back - either a normal reply or a HITL confirmation prompt"""
    response: str
    # confirmation id will be required when a tool needs confirmation
    # frontend uses this to send yes no back

    confirmation_id: Optional[str] = None

    # what type of confirmation: "github_ingest " or " cv_save"
    confirmation_type: Optional[str] = None
