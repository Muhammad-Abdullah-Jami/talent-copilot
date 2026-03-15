# init_db.py
# Run this once to create all tables in PostgreSQL
# After running, check pgAdmin — you'll see all 9 tables!

from backend.database import engine, Base

# This import triggers all models to register with Base
from backend.models import (
    Tenant, User, Session, Message, 
    SessionSummary, Candidate, Repository, 
    Confirmation, Job
)

print("Creating all tables...")
# This single line creates ALL tables that inherit from Base
Base.metadata.create_all(bind=engine)
print("Done! Check pgAdmin.")