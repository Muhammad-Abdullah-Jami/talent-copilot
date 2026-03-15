# frontend/app.py
# Streamlit chat UI for TalentCopilot
#
# Features:
#   - Chat interface with message history
#   - CV file upload (PDF/DOCX)
#   - Yes/No buttons for HITL confirmations
#   - Job status polling
#   - Tenant/User/Session selection
#   - Workspace viewer

import streamlit as st
import requests
import time
import json

# Backend API URL
API_URL = "http://127.0.0.1:8000"

# ---- Page Config ----
st.set_page_config(
    page_title="TalentCopilot",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 TalentCopilot")
st.caption("AI-powered recruiting assistant with HITL confirmation")


# ---- Sidebar: Tenant/User/Session ----
with st.sidebar:
    st.header("Session Settings")

    tenant_id = st.text_input("Tenant ID", value="tenant-a")
    user_id = st.text_input("User ID", value="user-1")
    session_id = st.text_input("Session ID", value="session-1")

    st.divider()

    # ---- CV Upload Section ----
    st.header("Upload CV")
    uploaded_file = st.file_uploader(
        "Upload a resume (PDF or DOCX)",
        type=["pdf", "docx"]
    )

    if uploaded_file and st.button("Parse CV"):
        with st.spinner("Parsing CV..."):
            files = {
                "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
            }
            data = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "session_id": session_id
            }
            try:
                resp = requests.post(f"{API_URL}/upload/cv", files=files, data=data)
                if resp.status_code == 200:
                    result = resp.json()
                    st.success(result["message"])

                    # Show parsed data
                    with st.expander("Parsed CV Data"):
                        st.json(result["parsed_data"])

                    # Store confirmation for HITL
                    if result.get("confirmation_id"):
                        st.session_state["pending_confirmation"] = {
                            "id": result["confirmation_id"],
                            "type": "cv_save",
                            "message": "Save this candidate profile to workspace?"
                        }
                else:
                    st.error(f"Error: {resp.text}")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Is the server running?")

    st.divider()

    # ---- Workspace Viewer ----
    st.header("Workspace")
    if st.button("Load Workspace"):
        try:
            resp = requests.get(
                f"{API_URL}/workspace",
                params={
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "session_id": session_id
                }
            )
            if resp.status_code == 200:
                workspace = resp.json()

                if workspace.get("candidates"):
                    st.subheader("Candidates")
                    for c in workspace["candidates"]:
                        st.write(f"**{c.get('name', 'Unknown')}** - {c.get('email', 'N/A')}")
                        st.write(f"Skills: {c.get('skills', 'N/A')}")
                        st.divider()
                else:
                    st.info("No candidates saved yet.")

                if workspace.get("repositories"):
                    st.subheader("Repositories")
                    for r in workspace["repositories"]:
                        st.write(f"**{r.get('repo_name', 'Unknown')}**")
                        st.write(f"URL: {r.get('repo_url', 'N/A')}")
                        st.divider()
                else:
                    st.info("No repositories ingested yet.")

                if workspace.get("session_summary"):
                    st.subheader("Session Summary")
                    st.write(workspace["session_summary"])
            else:
                st.error(f"Error: {resp.text}")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")


# ---- Initialize Chat History ----
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "pending_confirmation" not in st.session_state:
    st.session_state["pending_confirmation"] = None

if "active_jobs" not in st.session_state:
    st.session_state["active_jobs"] = []


# ---- Display Chat Messages ----
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# ---- HITL Confirmation Buttons ----
if st.session_state["pending_confirmation"]:
    confirmation = st.session_state["pending_confirmation"]

    st.info(f"⚠️ Confirmation needed: {confirmation['message']}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Yes, approve", key="confirm_yes"):
            resp = requests.post(
                f"{API_URL}/confirm",
                json={
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "confirmation_id": confirmation["id"],
                    "decision": "yes"
                }
            )
            if resp.status_code == 200:
                result = resp.json()
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": result["message"]
                })

                # If a job was created, track it
                if result.get("job_id"):
                    st.session_state["active_jobs"].append(result["job_id"])

                st.session_state["pending_confirmation"] = None
                st.rerun()
            else:
                st.error(f"Error: {resp.text}")

    with col2:
        if st.button("❌ No, cancel", key="confirm_no"):
            resp = requests.post(
                f"{API_URL}/confirm",
                json={
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "confirmation_id": confirmation["id"],
                    "decision": "no"
                }
            )
            if resp.status_code == 200:
                result = resp.json()
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": result["message"]
                })
                st.session_state["pending_confirmation"] = None
                st.rerun()
            else:
                st.error(f"Error: {resp.text}")


# ---- Job Status Tracker ----
if st.session_state["active_jobs"]:
    st.subheader("Active Jobs")

    jobs_to_remove = []
    has_running_jobs = False

    for job_id in st.session_state["active_jobs"]:
        try:
            resp = requests.get(f"{API_URL}/jobs/{job_id}")
            if resp.status_code == 200:
                job = resp.json()
                status = job["status"]

                if status == "succeeded":
                    st.success(f"Job {job_id[:8]}... completed! ✅")
                    jobs_to_remove.append(job_id)
                elif status == "failed":
                    st.error(f"Job {job_id[:8]}... failed: {job.get('error', 'Unknown error')}")
                    jobs_to_remove.append(job_id)
                elif status == "running":
                    st.warning(f"Job {job_id[:8]}... running ⏳")
                    has_running_jobs = True
                else:
                    st.info(f"Job {job_id[:8]}... queued")
                    has_running_jobs = True
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")

    # Clean up completed/failed jobs
    for job_id in jobs_to_remove:
        st.session_state["active_jobs"].remove(job_id)

    # Auto-refresh every 3 seconds while jobs are running
    if has_running_jobs:
        time.sleep(3)
        st.rerun()


# ---- Chat Input ----
user_input = st.chat_input("Type your message...")

if user_input:
    # Display user message
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Send to backend
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "message": user_input
                    }
                )

                if resp.status_code == 200:
                    result = resp.json()
                    response_text = result["response"]

                    # Display response
                    st.write(response_text)
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": response_text
                    })

                    # Check if HITL confirmation is needed
                    if result.get("confirmation_id"):
                        st.session_state["pending_confirmation"] = {
                            "id": result["confirmation_id"],
                            "type": result.get("confirmation_type", ""),
                            "message": response_text
                        }
                        st.rerun()

                else:
                    st.error(f"Error: {resp.text}")

            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to backend. Is the server running?")