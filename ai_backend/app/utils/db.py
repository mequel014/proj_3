# app/utils/db.py
from sqlmodel import SQLModel, create_engine, Session
from config import settings

# engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, connect_args={"check_same_thread": False})
engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session