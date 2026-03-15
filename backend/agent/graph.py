# agent/graph.py
# Wires all nodes into a LangGraph state machine.
#
# The graph looks like this:
#
#   START
#     │
#     ▼
#   conversation_node  (LLM analyzes message)
#     │
#     ▼
#   check_tool_node  (tool needed?)
#     │
#     ├── NO  ──→  response_node  ──→  END
#     │
#     └── YES ──→  create_confirmation_node  ──→  END
#
# If confirmation is needed, the graph ENDS and returns a
# confirmation prompt. The /confirm endpoint handles the rest.

from langgraph.graph import StateGraph, END
from backend.agent.states import AgentState
from backend.agent.nodes import (
    conversation_node,
    check_tool_node,
    create_confirmation_node,
    response_node
)


def route_after_check(state: AgentState) -> str:
    """
    Conditional edge: decides which node comes after check_tool_node.
    
    LangGraph calls this function to decide the next step:
    - If tool needed → go to confirmation
    - If no tool → go straight to response
    
    Returns the NAME of the next node (as a string).
    """
    if state.get("needs_tool"):
        return "create_confirmation"
    return "response"


def build_graph():
    """
    Builds and compiles the LangGraph.
    
    Steps:
    1. Create a StateGraph with our state type
    2. Add nodes (each is a function)
    3. Add edges (connections between nodes)
    4. Add conditional edges (branching logic)
    5. Set entry point
    6. Compile
    
    The compiled graph is a runnable object:
        result = graph.invoke({"user_message": "...", ...})
    """
    # Create graph with our state schema
    graph = StateGraph(AgentState)

    # Add nodes — name them, point to functions
    graph.add_node("conversation", conversation_node)
    graph.add_node("check_tool", check_tool_node)
    graph.add_node("create_confirmation", create_confirmation_node)
    graph.add_node("response", response_node)

    # Set where the graph starts
    graph.set_entry_point("conversation")

    # Add edges — fixed connections
    graph.add_edge("conversation", "check_tool")

    # Conditional edge — branching based on state
    graph.add_conditional_edges(
        "check_tool",           # from this node
        route_after_check,      # use this function to decide
        {
            "create_confirmation": "create_confirmation",  # if returns this → go here
            "response": "response"                          # if returns this → go here
        }
    )

    # Both confirmation and response lead to END
    graph.add_edge("create_confirmation", END)
    graph.add_edge("response", END)

    # Compile the graph — makes it runnable
    return graph.compile()


# Create a single instance to use throughout the app
agent_graph = build_graph()