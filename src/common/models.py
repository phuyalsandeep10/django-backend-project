
from sqlmodel import SQLModel, Field
import sqlalchemy as sa
import datetime

class CommonModel(SQLModel):
    id: int = Field(default=None, primary_key=True)
    active: bool = Field(default=True, nullable=False)

    user_id: int = Field(
        foreign_key="sys_users.id", 
        nullable=False
    )  # Assuming a User model exists with id as primary key

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


