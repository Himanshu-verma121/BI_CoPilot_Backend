from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings
from models.models import Base


from sqlalchemy import create_engine

if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)
else:
    engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

def get_db():
    db = SessionLocal()
    try:
        yield db        
    finally:
        db.close()      