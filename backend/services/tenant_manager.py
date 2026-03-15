# services/tenant_manager.py
# Auto-creates tenant, user, and session if they don't exist.
# This makes the app easy to use — no manual setup needed.

from sqlalchemy.orm import Session
from backend.models.tenant import Tenant
from backend.models.user import User
from backend.models.session import Session as ChatSession


def ensure_tenant_user_session(db: Session, tenant_id: str, user_id: str, session_id: str):
    """
    Make sure tenant, user, and session exist in the database.
    Creates them if they don't exist. Skips if they already do.
    
    This is called at the start of every request so the app
    works without manual setup.
    """
    # Check/create tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        tenant = Tenant(id=tenant_id, name=f"Tenant {tenant_id}")
        db.add(tenant)
        db.commit()

    # Check/create user
    user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
    if not user:
        user = User(id=user_id, tenant_id=tenant_id, name=f"User {user_id}")
        db.add(user)
        db.commit()

    # Check/create session
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.tenant_id == tenant_id
    ).first()
    if not session:
        session = ChatSession(id=session_id, tenant_id=tenant_id, user_id=user_id)
        db.add(session)
        db.commit()