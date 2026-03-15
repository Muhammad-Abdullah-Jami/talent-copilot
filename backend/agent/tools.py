# agent/tools.py
# Defines what tools the agent can use.
# These are NOT the implementations — just descriptions.
# The LLM reads these descriptions to decide WHEN to use a tool.
#
# Important: Tools here don't execute directly.
# They go through HITL confirmation first.

import json
from backend.models.candidate import Candidate
from backend.models.repository import Repository


# Tool definitions as simple dicts
# The LLM will see these in its system prompt

TOOL_DEFINITIONS = """
You have access to the following tools:

1. github_ingest
   - Use when: user shares a GitHub repository URL and wants it analyzed
   - Input: repo_url (the GitHub URL)
   - What it does: crawls the repo, extracts README, file structure, languages, code snippets
   - REQUIRES user confirmation before execution

2. cv_save  
   - Use when: a CV has been parsed and needs to be saved to the workspace
   - Input: candidate_data (the parsed CV data as JSON)
   - What it does: saves the candidate profile to the workspace
   - REQUIRES user confirmation before execution

IMPORTANT RULES:
- If a tool is needed, respond with EXACTLY this JSON format:
  {"tool_needed": true, "tool_name": "github_ingest", "tool_payload": {"repo_url": "https://github.com/..."}}
  OR
  {"tool_needed": true, "tool_name": "cv_save", "tool_payload": {"candidate_data": "..."}}
- If NO tool is needed, just respond normally as a helpful recruiting assistant.
- NEVER execute tools without asking for confirmation first.
"""


def get_workspace_context(db, tenant_id: str, user_id: str):
    """
    Fetch workspace artifacts (candidates + repos) so the LLM can
    answer questions about them.
    
    This is called when building the LLM prompt so it knows what
    data is available in the workspace.
    """
    candidates = db.query(Candidate).filter(
        Candidate.tenant_id == tenant_id,
        Candidate.user_id == user_id
    ).all()

    repos = db.query(Repository).filter(
        Repository.tenant_id == tenant_id,
        Repository.user_id == user_id
    ).all()

    context = ""

    if candidates:
        context += "\n--- SAVED CANDIDATES ---\n"
        for c in candidates:
            context += f"Name: {c.name}\n"
            context += f"Skills: {c.skills}\n"
            context += f"Experience: {c.experience}\n"
            context += f"Education: {c.education}\n"
            context += f"Projects: {c.projects}\n\n"

    if repos:
        context += "\n--- INGESTED REPOSITORIES ---\n"
        for r in repos:
            context += f"Repo: {r.repo_name} ({r.repo_url})\n"
            context += f"Languages: {r.languages}\n"
            context += f"README: {r.readme_content[:500] if r.readme_content else 'N/A'}\n"
            context += f"File Tree: {r.file_tree}\n\n"

    return context