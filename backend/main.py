# main.py
# FastAPI application entry point
# This file wires everything together: routers, DB, CORS

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base

# Import all models so tables get created on startup
from backend.models import (
    Tenant, User, Session, Message,
    SessionSummary, Candidate, Repository,
    Confirmation, Job
)

# Import all routers
from backend.routers import (
    chat_router,
    confirm_router,
    upload_router,
    ingest_router,
    jobs_router,
    workspace_router
)

# Create the FastAPI app
app = FastAPI(
    title="TalentCopilot API",
    description="Multi-tenant recruiting chatbot with HITL confirmation",
    version="1.0.0"
)

# CORS middleware — allows frontend (Streamlit) to talk to backend
# Without this, browser blocks requests from different ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production, restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create all DB tables on startup (safe to run multiple times — skips existing)
Base.metadata.create_all(bind=engine)

# Mount all routers — each one adds its endpoints to the app
app.include_router(chat_router)
app.include_router(confirm_router)
app.include_router(upload_router)
app.include_router(ingest_router)
app.include_router(jobs_router)
app.include_router(workspace_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "TalentCopilot API is running"}