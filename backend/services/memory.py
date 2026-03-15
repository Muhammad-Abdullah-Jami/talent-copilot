# services/memory.py
# Handles all chat memory operations:
# 1. Save messages to DB
# 2. Load recent messages (windowing)
# 3. Summarize old messages when conversation gets long
#
# Memory windowing strategy:
#   - Keep last N messages as full text (N=10 by default)
#   - Everything older gets summarized into a single summary record
#   - When chatting, LLM sees: [summary] + [last 10 messages]

import json
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from backend.models.message import Message
from backend.models.session_summary import SessionSummary
from backend.config import OPENAI_API_KEY

# How many recent messages to keep in full
MEMORY_WINDOW_SIZE = 10

# LLM used for summarization (cheap model is fine for summaries)
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0
)


def save_message(db: Session, session_id: str, tenant_id: str, role: str, content: str):
    """
    Save a single message to the database.
    Called after every user message and every assistant response.
    
    Args:
        db: database session
        session_id: which chat session this belongs to
        tenant_id: which tenant (for isolation)
        role: "user" or "assistant"
        content: the message text
    
    How sequence works:
        We count existing messages in this session and add 1.
        This gives us ordering without timestamps (which can collide).
    """
    # Count existing messages to get next sequence number
    count = db.query(Message).filter(
        Message.session_id == session_id,
        Message.tenant_id == tenant_id
    ).count()

    message = Message(
        session_id=session_id,
        tenant_id=tenant_id,
        role=role,
        content=content,
        sequence=count + 1
    )
    db.add(message)
    db.commit()
    return message


def get_recent_messages(db: Session, session_id: str, tenant_id: str):
    """
    Get the last N messages for this session.
    These are the messages the LLM will see in full detail.
    
    Returns list of dicts: [{"role": "user", "content": "..."}, ...]
    This format matches what LangChain expects.
    """
    messages = db.query(Message).filter(
        Message.session_id == session_id,
        Message.tenant_id == tenant_id
    ).order_by(
        Message.sequence.desc()  # newest first
    ).limit(MEMORY_WINDOW_SIZE).all()

    # Reverse so they're in chronological order (oldest first)
    messages.reverse()

    return [{"role": m.role, "content": m.content} for m in messages]


def get_session_summary(db: Session, session_id: str, tenant_id: str):
    """
    Get the most recent summary for this session.
    Returns the summary text, or None if no summary exists yet.
    """
    summary = db.query(SessionSummary).filter(
        SessionSummary.session_id == session_id,
        SessionSummary.tenant_id == tenant_id
    ).order_by(
        SessionSummary.created_at.desc()
    ).first()

    if summary:
        return summary.summary
    return None


def get_total_message_count(db: Session, session_id: str, tenant_id: str):
    """Helper: count all messages in a session"""
    return db.query(Message).filter(
        Message.session_id == session_id,
        Message.tenant_id == tenant_id
    ).count()


def get_messages_for_summarization(db: Session, session_id: str, tenant_id: str):
    """
    Get the OLD messages that need to be summarized.
    These are all messages EXCEPT the recent window.
    
    Example: 25 messages total, window=10
    → Messages 1-15 get summarized, messages 16-25 stay in full
    """
    total = get_total_message_count(db, session_id, tenant_id)

    if total <= MEMORY_WINDOW_SIZE:
        return []  # not enough messages to need summarization

    # Get all messages except the recent window
    old_messages = db.query(Message).filter(
        Message.session_id == session_id,
        Message.tenant_id == tenant_id
    ).order_by(
        Message.sequence.asc()
    ).limit(total - MEMORY_WINDOW_SIZE).all()

    return [{"role": m.role, "content": m.content} for m in old_messages]


def summarize_old_messages(db: Session, session_id: str, tenant_id: str):
    """
    Summarize old messages and store the summary in DB.
    
    This runs when conversation gets long. It:
    1. Gets old messages (everything outside the recent window)
    2. Sends them to LLM with a summarization prompt
    3. Saves the summary to session_summaries table
    
    The summary REPLACES old messages in the context, so the LLM
    sees: [summary of messages 1-15] + [full messages 16-25]
    """
    old_messages = get_messages_for_summarization(db, session_id, tenant_id)

    if not old_messages:
        return None  # nothing to summarize

    # Build a text version of old messages for the LLM
    conversation_text = ""
    for msg in old_messages:
        conversation_text += f"{msg['role']}: {msg['content']}\n"

    # Ask LLM to summarize
    summary_prompt = f"""Summarize the following conversation concisely.
Focus on: key topics discussed, decisions made, candidate details mentioned,
repo information shared, and any pending actions.

Conversation:
{conversation_text}

Summary:"""

    response = llm.invoke(summary_prompt)
    summary_text = response.content

    total = get_total_message_count(db, session_id, tenant_id)

    # Save summary to DB
    summary = SessionSummary(
        session_id=session_id,
        tenant_id=tenant_id,
        summary=summary_text,
        messages_summarized_up_to=total - MEMORY_WINDOW_SIZE
    )
    db.add(summary)
    db.commit()

    return summary_text


def build_context(db: Session, session_id: str, tenant_id: str):
    """
    Build the full context that the LLM will see.
    This is the MAIN function other code will call.
    
    Returns a list of message dicts ready for LangChain:
    [
        {"role": "system", "content": "Summary of earlier conversation: ..."},
        {"role": "user", "content": "recent message 1"},
        {"role": "assistant", "content": "recent response 1"},
        ...
    ]
    
    Logic:
    1. If conversation is long enough, trigger summarization
    2. Get summary (if exists)
    3. Get recent messages
    4. Combine: summary + recent messages
    """
    total = get_total_message_count(db, session_id, tenant_id)

    # If conversation is long enough, summarize old messages
    if total > MEMORY_WINDOW_SIZE:
        summarize_old_messages(db, session_id, tenant_id)

    context = []

    # Add summary if it exists
    summary = get_session_summary(db, session_id, tenant_id)
    if summary:
        context.append({
            "role": "system",
            "content": f"Summary of earlier conversation: {summary}"
        })

    # Add recent messages
    recent = get_recent_messages(db, session_id, tenant_id)
    context.extend(recent)

    return context
