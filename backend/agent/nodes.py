# agent/nodes.py
# Each function here is a NODE in the LangGraph.
# Nodes are processing steps. Data flows: node1 → node2 → node3
#
# Our nodes:
#   1. conversation_node — LLM analyzes the message
#   2. check_tool_node — decides: tool needed or just respond?
#   3. create_confirmation_node — creates a HITL confirmation record
#   4. response_node — builds the final response

import json
import uuid
from langchain_openai import ChatOpenAI
from backend.agent.states import AgentState
from backend.agent.tools import TOOL_DEFINITIONS, get_workspace_context
from backend.config import OPENAI_API_KEY
from backend.database import SessionLocal
from backend.models.confirmation import Confirmation

# The LLM that powers the agent
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0.3
)


def conversation_node(state: AgentState) -> dict:
    """
    Node 1: Send the user message + history to the LLM.
    
    The LLM either:
    - Responds normally (no tool needed)
    - Returns a JSON indicating a tool is needed
    
    This node builds the full prompt with:
    - System instructions + tool definitions
    - Workspace context (saved candidates, repos)
    - Chat history (from memory system)
    - Current user message
    """
    db = SessionLocal()

    try:
        # Get workspace data so LLM can answer questions about it
        workspace = get_workspace_context(
            db, state["tenant_id"], state["user_id"]
        )

        # Build the system prompt
        system_prompt = f"""You are TalentCopilot, an AI recruiting assistant.
You help recruiting teams evaluate candidates and repositories.

You can:
- Answer questions about candidates (from their CVs)
- Answer questions about GitHub repositories (structure, stack, quality)
- Generate interview questions and evaluation notes
- Have normal conversations about recruiting

{TOOL_DEFINITIONS}

{workspace}

CRITICAL INSTRUCTION FOR TOOL DETECTION:
- If the user message contains a GitHub URL (github.com/...), you MUST respond with ONLY this JSON:
  {{"tool_needed": true, "tool_name": "github_ingest", "tool_payload": {{"repo_url": "THE_URL"}}}}
- Do NOT ask the user to confirm. Do NOT respond conversationally when a tool is needed. Just return the JSON.
- If the user asks QUESTIONS about an already-ingested repo (like "what is this repo about"), answer directly from the workspace data. Only trigger the tool if the message contains a URL.
- If no tool is needed, respond normally as a helpful recruiting assistant.
- NEVER return {{"tool_needed": false}} as a response. Either return the tool JSON or respond normally in plain English.

Remember: Be helpful, concise, and professional."""

        # Build messages for the LLM
        messages = [{"role": "system", "content": system_prompt}]

        # Add chat history from memory
        for msg in state["chat_history"]:
            messages.append(msg)

        # Add current user message
        messages.append({"role": "user", "content": state["user_message"]})

        # Call the LLM
        response = llm.invoke(messages)
        response_text = response.content

        return {"response": response_text}

    finally:
        db.close()


def check_tool_node(state: AgentState) -> dict:
    """
    Node 2: Check if the LLM's response indicates a tool is needed.
    
    We look at the response text. If it contains our special JSON format
    {"tool_needed": true, ...}, we extract the tool info.
    Otherwise, it's a normal response.
    
    Also handles the case where LLM returns {"tool_needed": false}
    by replacing the response with a helpful fallback message.
    """
    response_text = state["response"]

    try:
        parsed = json.loads(response_text)

        if parsed.get("tool_needed") is True:
            return {
                "needs_tool": True,
                "tool_name": parsed["tool_name"],
                "tool_payload": json.dumps(parsed["tool_payload"])
            }
        else:
            # LLM returned JSON with tool_needed=false
            # Replace with a normal response so user doesn't see raw JSON
            return {
                "needs_tool": False,
                "tool_name": None,
                "tool_payload": None,
                "response": "I'm here to help! You can ask me about candidates, repositories, or anything related to recruiting."
            }
    except (json.JSONDecodeError, KeyError):
        # Not JSON = normal conversational response (this is good)
        pass

    return {"needs_tool": False, "tool_name": None, "tool_payload": None}


def create_confirmation_node(state: AgentState) -> dict:
    """
    Node 3: Create a HITL confirmation record in the database.
    
    This runs ONLY when a tool is needed. It:
    1. Creates a confirmation record with status "pending"
    2. Builds a human-friendly confirmation message
    3. Returns the confirmation_id so frontend can send yes/no
    
    The tool does NOT execute here. It waits for user approval
    via the /confirm endpoint.
    """
    db = SessionLocal()

    try:
        confirmation = Confirmation(
            id=str(uuid.uuid4()),
            tenant_id=state["tenant_id"],
            user_id=state["user_id"],
            session_id=state["session_id"],
            tool_name=state["tool_name"],
            tool_payload=state["tool_payload"],
            status="pending"
        )
        db.add(confirmation)
        db.commit()

        # Build a user-friendly confirmation message
        if state["tool_name"] == "github_ingest":
            payload = json.loads(state["tool_payload"])
            message = f"Would you like me to crawl this repository: {payload.get('repo_url', '')} ? (yes/no)"
        elif state["tool_name"] == "cv_save":
            message = "Do you want me to save this candidate profile to the workspace? (yes/no)"
        else:
            message = f"Do you want me to execute {state['tool_name']}? (yes/no)"

        return {
            "confirmation_id": confirmation.id,
            "response": message
        }

    finally:
        db.close()


def response_node(state: AgentState) -> dict:
    """
    Node 4: Final node — just passes through the response.
    
    This exists as a clean endpoint for the graph.
    In a more complex system, you might do post-processing here
    (like content filtering, formatting, etc.)
    """
    return {"response": state["response"]}