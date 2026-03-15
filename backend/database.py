from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()

def get_db():
    """
    Dependency function for FastAPI.
    Creates a new DB session for each request, closes it when done.
    FastAPI calls this automatically when your endpoint needs a DB session.
    
    Usage in a router:
        def my_endpoint(db: Session = Depends(get_db)):
            db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db  # give the session to the endpoint
    finally:
        db.close()  # always close when request is done
