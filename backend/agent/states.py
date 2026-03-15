# agent/states.py
# Defines the state that flows through the LangGraph
#
# Think of state as a "packet of data" that every node in the graph
# can read and modify. It flows from node to node like a baton in a relay.

from typing import TypedDict, Optional, List


class AgentState(TypedDict):
    """
    The data that flows through every node in the graph.
    Each node can read any field and return updates to any field.
    
    Fields:
        tenant_id, user_id, session_id: scoping (who is this?)
        user_message: what the user just said
        chat_history: past messages loaded from memory
        needs_tool: did the LLM decide a tool is needed?
        tool_name: which tool? "github_ingest" or "cv_save"
        tool_payload: data for the tool (e.g., repo URL)
        confirmation_id: ID of the pending confirmation record
        response: the final text response to send back to user
    """
    tenant_id: str
    user_id: str
    session_id: str
    user_message: str
    chat_history: List[dict]          # [{"role": "user", "content": "..."}]
    needs_tool: bool
    tool_name: Optional[str]
    tool_payload: Optional[str]       # JSON string
    confirmation_id: Optional[str]
    response: str