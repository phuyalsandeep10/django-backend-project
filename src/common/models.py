
from sqlmodel import SQLModel, Field, Session,select
import sqlalchemy as sa
from datetime import datetime
from typing import Type, TypeVar,List
from src.config.database import get_session

T = TypeVar('T')

def case_insensitive(attributes):
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            async with Session() as session:
                query = session.query(self)
            for key, value in kwargs.items():
                if key in attributes:
                    query = query.filter(func.lower(getattr(self, key)) == value.lower())
            else:
                query = query.filter(getattr(self, key) == value)
            return await query.all()
        return wrapper
    return decorator


class CommonModel(SQLModel):
    id: int = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)
    created_by_id: int = Field(foreign_key="sys_users.id", nullable=False)
    updated_by_id: int = Field(foreign_key="sys_users.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


    @classmethod
    async def get(cls: Type[T], id: int) -> T:
        async with Session() as session:
            return await session.get(cls, id)

    @classmethod
    async def get_all(cls: Type[T]) -> list[T]:
        async with Session() as session:
            return await session.query(cls).all()

    @classmethod
    async def create(cls: Type[T], **kwargs) -> T:
        async with Session() as session:
            obj = cls(**kwargs)
            session.add(obj)
            await session.commit()
            return obj

    @classmethod
    async def update(cls: Type[T], id: int, **kwargs) -> T:
        async with Session() as session:
            obj = await session.get(cls, id)
            if obj:
                for key, value in kwargs.items():
                    setattr(obj, key, value)
                await session.commit()
            return obj

    @classmethod
    async def delete(cls: Type[T], id: int) -> None:
        async with Session() as session:
            obj = await session.get(cls, id)
            if obj:
                session.delete(obj)
                await session.commit()

    @classmethod
    async def filter(cls: Type[T], **kwargs) -> list[T]:
      
        async with Session() as session:
            return await session.query(cls).filter_by(**kwargs).all()
    

    @classmethod
    async def filter(cls: Type[T], **kwargs) -> List[T]:
        async with Session() as session:
            query = session.query(cls)
            for key, value in kwargs.items():
                query = query.filter(getattr(cls, key) == value)
            return await query.all()

    @classmethod
    async def filter_or(cls: Type[T], **kwargs) -> List[T]:
        async with Session() as session:
            query = session.query(cls)
        for key, value in kwargs.items():
            query = query.filter(getattr(cls, key).like(f'%{value}%'))
        return await query.all()
    
    @classmethod
    async def filter_paginated(cls: Type[T], limit: int = 100, offset: int = 0, **kwargs) -> List[T]:
        async with Session() as session:
            query = session.query(cls)
            for key, value in kwargs.items():
                query = query.filter(getattr(cls, key) == value)
            return await query.limit(limit).offset(offset).all()
    

    class Config:
        orm_mode = True
        # arbitrary_types_allowed = True



class Permissions(SQLModel,table=True):
    __tablename__ = "sys_permissions"
    
    id: int = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, nullable=False, index=True)
    identifier: str = Field(max_length=255, nullable=False, unique=True, index=True)

    description: str = Field(default=None, max_length=500, nullable=True)

    created_at: datetime = Field(
        sa_column=sa.Column(
            sa.DateTime, 
            default=datetime.utcnow,
    
            nullable=False
        )
    )
    
    updated_at: datetime = Field(
        sa_column=sa.Column(
            sa.DateTime, 
            default=datetime.utcnow, 
            onupdate=datetime.utcnow, 
            nullable=False
        )
    )
