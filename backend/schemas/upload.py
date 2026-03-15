# schemas/upload.py
# For CV upload endpoint

from pydantic import BaseModel
from typing import Optional


class CVUploadResponse(BaseModel):
    """Returned after parsing a CV — shows parsed data + asks for save confirmation"""
    message: str
    parsed_data: dict  # the structured CV data
    confirmation_id: Optional[str] = None  # for the "save to workspace?" prompt