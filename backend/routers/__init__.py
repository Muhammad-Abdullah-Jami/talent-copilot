# routers/__init__.py
# Import all routers for easy access from main.py

from backend.routers.chat import router as chat_router
from backend.routers.confirm import router as confirm_router
from backend.routers.upload import router as upload_router
from backend.routers.ingest import router as ingest_router
from backend.routers.jobs import router as jobs_router
from backend.routers.workspace import router as workspace_router