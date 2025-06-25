
from sqlmodel import SQLModel, Field
import sqlalchemy as sa
import datetime

class CommonModel(SQLModel):
    id: int = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    created_by_id: int = Field(
        foreign_key="sys_users.id", 
        nullable=False
    )  # Assuming a User model exists with id as primary key

    updated_by_id: int = Field(
        foreign_key="sys_users.id", 
        nullable=False
    )

    

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
    

    # class Config:
    #     orm_mode = True
    #     arbitrary_types_allowed = True



class Permissions(SQLModel,table=True):
    __tablename__ = "sys_permissions"
    
    id: int = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, nullable=False, index=True)
    identifier: str = Field(max_length=255, nullable=False, unique=True, index=True)

    description: str = Field(default=None, max_length=500, nullable=True)

    created_at: datetime = Field(
        sa_column=sa.Column(
            sa.DateTime, 
            default=datetime.utcn
    
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
