# routers/chat.py
# Main chat endpoint — now wired to the LangGraph agent

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.memory import save_message, build_context
from backend.agent.graph import agent_graph
from backend.services.tenant_manager import ensure_tenant_user_session

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Main chat endpoint. Here's what happens step by step:
    
    1. Save the user's message to DB (memory)
    2. Build context (summary + recent messages)
    3. Run the LangGraph agent
    4. Save the assistant's response to DB (memory)
    5. Return the response (with confirmation_id if tool needed)
    """
    ensure_tenant_user_session(db, request.tenant_id, request.user_id, request.session_id)
    # Step 1: Save user message
    save_message(
        db, request.session_id, request.tenant_id,
        "user", request.message
    )

    # Step 2: Build memory context
    chat_history = build_context(
        db, request.session_id, request.tenant_id
    )

    # Step 3: Run the agent graph
    result = agent_graph.invoke({
        "tenant_id": request.tenant_id,
        "user_id": request.user_id,
        "session_id": request.session_id,
        "user_message": request.message,
        "chat_history": chat_history,
        "needs_tool": False,
        "tool_name": None,
        "tool_payload": None,
        "confirmation_id": None,
        "response": ""
    })

    # Step 4: Save assistant response
    save_message(
        db, request.session_id, request.tenant_id,
        "assistant", result["response"]
    )

    # Step 5: Return response
    return ChatResponse(
        response=result["response"],
        confirmation_id=result.get("confirmation_id"),
        confirmation_type=result.get("tool_name")
    )