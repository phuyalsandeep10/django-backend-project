from sqlmodel import Field, Session, SQLModel, create_engine, select,Session
from typing import Annotated
from fastapi import Depends

DATABASE_URL = "sqlite:///./db.sqlite"  # Update with your database URL
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get a new SQLModel session."""
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
