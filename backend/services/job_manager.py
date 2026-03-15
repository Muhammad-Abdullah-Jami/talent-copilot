# services/job_manager.py
# Manages background jobs for long-running operations.
#
# Why background jobs?
# GitHub ingestion can take 10-30 seconds (multiple API calls).
# We don't want the chat to freeze while waiting.
#
# Flow:
#   1. /confirm creates a Job with status="queued"
#   2. job_manager picks it up and runs it in a background thread
#   3. Job status updates: queued → running → succeeded/failed
#   4. Frontend polls GET /jobs/{job_id} to check progress

import json
import threading
from datetime import datetime
from backend.database import SessionLocal
from backend.models.job import Job
from backend.models.repository import Repository
from backend.services.github_ingestor import ingest_repo


def run_github_ingestion(job_id: str, tenant_id: str, user_id: str):
    """
    Background function that runs GitHub ingestion.
    
    This runs in a SEPARATE THREAD so it doesn't block the main app.
    It creates its own DB session (each thread needs its own session).
    
    Steps:
    1. Mark job as "running"
    2. Call ingest_repo() — the actual work
    3. Save results to repositories table
    4. Mark job as "succeeded"
    5. If anything fails, mark as "failed" with error message
    """
    # Each thread needs its own DB session
    db = SessionLocal()

    try:
        # Get the job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        # Mark as running
        job.status = "running"
        job.updated_at = datetime.utcnow()
        db.commit()

        # Parse the payload to get repo_url
        payload = json.loads(job.payload)
        repo_url = payload.get("repo_url", "")

        # Check if repo already ingested (idempotent)
        existing = db.query(Repository).filter(
            Repository.tenant_id == tenant_id,
            Repository.user_id == user_id,
            Repository.repo_url == repo_url
        ).first()

        if existing:
            # Update existing repo instead of creating duplicate
            result = ingest_repo(repo_url)
            existing.repo_name = result.get("repo_name")
            existing.readme_content = result.get("readme_content", "")
            existing.file_tree = json.dumps(result.get("file_tree", []))
            existing.languages = json.dumps(result.get("languages", {}))
            existing.stack_signals = json.dumps(result.get("stack_signals", []))
            existing.code_snippets = json.dumps(result.get("code_snippets", []))
        else:
            # Run ingestion
            result = ingest_repo(repo_url)

            # Save to repositories table
            repo = Repository(
                tenant_id=tenant_id,
                user_id=user_id,
                repo_url=repo_url,
                repo_name=result.get("repo_name"),
                readme_content=result.get("readme_content", ""),
                file_tree=json.dumps(result.get("file_tree", [])),
                languages=json.dumps(result.get("languages", {})),
                stack_signals=json.dumps(result.get("stack_signals", [])),
                code_snippets=json.dumps(result.get("code_snippets", []))
            )
            db.add(repo)

        # Mark job as succeeded
        job.status = "succeeded"
        job.result = json.dumps({"repo_url": repo_url, "message": "Ingestion complete"})
        job.updated_at = datetime.utcnow()
        db.commit()

        print(f"Job {job_id} completed successfully: {repo_url}")

    except Exception as e:
        # Mark job as failed
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error = str(e)
                job.updated_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        print(f"Job {job_id} failed: {str(e)}")

    finally:
        db.close()


def start_ingestion_job(job_id: str, tenant_id: str, user_id: str):
    """
    Start a GitHub ingestion job in a background thread.
    
    threading.Thread creates a new thread that runs independently.
    daemon=True means it dies when the main app dies (no zombie threads).
    
    This returns immediately — the caller doesn't wait for ingestion.
    """
    thread = threading.Thread(
        target=run_github_ingestion,
        args=(job_id, tenant_id, user_id),
        daemon=True
    )
    thread.start()
    return thread