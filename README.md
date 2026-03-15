# TalentCopilot

AI-powered multi-tenant recruiting assistant with Human-in-the-Loop (HITL) confirmation for tool actions. Built with FastAPI, LangChain, LangGraph, and Streamlit.

## Features

- **Conversational AI Chat** — Ask questions about candidates, repositories, and recruiting
- **CV Parsing (HITL-gated)** — Upload PDF/DOCX resumes, parsed with LLM into structured data. Saving requires explicit user approval
- **GitHub Repo Ingestion (HITL-gated)** — Crawl public repos to extract README, file tree, languages, stack signals. Ingestion requires explicit user approval
- **Multi-Tenant Isolation** — All data scoped by tenant_id. Tenant A cannot access Tenant B's data
- **Persisted Memory with Windowing** — Messages stored in PostgreSQL. Recent messages kept in full, older messages summarized automatically
- **Background Job Execution** — Long-running GitHub ingestion runs in background threads with status tracking

## Architecture
```
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment variable loader
│   ├── database.py          # SQLAlchemy engine + session
│   ├── init_db.py           # One-time table creation script
│   ├── models/              # SQLAlchemy ORM models (9 tables)
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── message.py
│   │   ├── session_summary.py
│   │   ├── candidate.py
│   │   ├── repository.py
│   │   ├── confirmation.py
│   │   └── job.py
│   ├── schemas/             # Pydantic request/response models
│   ├── routers/             # FastAPI route handlers
│   │   ├── chat.py          # POST /chat
│   │   ├── confirm.py       # POST /confirm
│   │   ├── upload.py        # POST /upload/cv
│   │   ├── ingest.py        # POST /ingest/github
│   │   ├── jobs.py          # GET /jobs/{job_id}
│   │   └── workspace.py     # GET /workspace
│   ├── services/            # Business logic
│   │   ├── memory.py        # Chat memory + windowing + summarization
│   │   ├── cv_parser.py     # PDF/DOCX text extraction + LLM parsing
│   │   ├── github_ingestor.py  # GitHub API client
│   │   ├── job_manager.py   # Background job runner
│   │   └── tenant_manager.py   # Auto-creates tenant/user/session
│   └── agent/               # LangGraph agent
│       ├── states.py        # Graph state definition
│       ├── tools.py         # Tool definitions + workspace context
│       ├── nodes.py         # Graph nodes (conversation, check_tool, confirmation, response)
│       └── graph.py         # LangGraph wiring + compilation
├── frontend/
│   └── app.py               # Streamlit chat UI
├── requirements.txt
└── .env.example
```

## LangGraph HITL Flow
```
User Message → conversation_node (LLM) → check_tool_node
  → No tool needed  → response_node → Return response
  → Tool needed     → create_confirmation_node → Return confirmation prompt
                         ↓
                    User clicks Yes/No
                         ↓
                    POST /confirm
                      → Yes: Execute tool (save CV / start ingestion job)
                      → No:  Mark denied, continue chat
```

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, PostgreSQL
- **AI/Agent:** LangChain, LangGraph, OpenAI GPT-4o-mini
- **Frontend:** Streamlit
- **CV Parsing:** PyPDF2, python-docx
- **GitHub Integration:** GitHub REST API via httpx

## Prerequisites

- Python 3.10+
- PostgreSQL installed and running
- OpenAI API key
- GitHub Personal Access Token (optional, increases rate limits)

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/talent-copilot.git
cd talent-copilot
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create PostgreSQL database
```bash
sudo -u postgres psql
CREATE DATABASE talent_copilot;
\q
```

### 5. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 6. Initialize database tables
```bash
python -m backend.init_db
```

### 7. Start the backend
```bash
uvicorn backend.main:app --reload --port 8000
```

### 8. Start the frontend (new terminal)
```bash
source venv/bin/activate
streamlit run frontend/app.py
```

### 9. Open the app

- Frontend: http://localhost:8501
- API Docs: http://localhost:8000/docs

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /chat | Send message, get response or HITL prompt |
| POST | /confirm | Approve/deny pending confirmation |
| POST | /upload/cv | Upload and parse CV (PDF/DOCX) |
| POST | /ingest/github | Start repo ingestion (after approval) |
| GET | /jobs/{job_id} | Check background job status |
| GET | /workspace | Get tenant workspace snapshot |

## Example Flows

### Flow 1: CV Upload + Save
1. Upload a PDF/DOCX resume via sidebar
2. View parsed candidate data
3. Click "Yes, approve" to save to workspace
4. Ask questions: "What skills does this candidate have?"

### Flow 2: GitHub Repo Analysis
1. Chat: "Analyze this repo: https://github.com/pallets/flask"
2. Agent asks for confirmation
3. Click "Yes, approve" → ingestion job starts
4. Job completes → ask questions about the repo

### Flow 3: Tenant Isolation
1. Use Tenant A → upload CV, ingest repo
2. Switch to Tenant B → workspace is empty
3. Tenant B cannot see Tenant A's data

### Flow 4: Memory Windowing
1. Have a long conversation (10+ messages)
2. Older messages are automatically summarized
3. Assistant remains consistent using summary + recent context

## Data Model

9 tables with tenant scoping:
- **tenants** — company/team
- **users** — users within tenants
- **sessions** — chat threads
- **messages** — all chat messages
- **session_summaries** — LLM-generated summaries of old messages
- **candidates** — parsed CV profiles (saved after HITL approval)
- **repositories** — ingested GitHub repo data (saved after HITL approval)
- **confirmations** — HITL approval records (pending/approved/denied)
- **jobs** — background job tracking (queued/running/succeeded/failed)