from sqlmodel import Field, Session, SQLModel, create_engine, select,Session
from typing import Annotated
from fastapi import Depends
import os
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")# Updated to use PostgreSQL
engine = create_engine(DATABASE_URL)

def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get a new SQLModel session."""
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
