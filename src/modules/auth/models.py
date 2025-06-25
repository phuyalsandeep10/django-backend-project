
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime
import sqlalchemy as sa




class User(SQLModel, table=True):
    __tablename__ = "sys_users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: Optional[str] = None
    image: Optional[str] = None
    mobile: Optional[str] = Field(default=None, unique=True)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    is_active: bool = Field(default=True)
    email_verified_at: datetime = Field(default=None, nullable=True, )
    is_superuser: bool = Field(default=False)
    is_staff: bool = Field(default=False)


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


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="sys_users.id")
    token: str = Field(unique=True, index=True)
    active: bool = Field(default=False)
    created_at: Optional[str] = None  # Use appropriate datetime type if needed
    expires_at: Optional[str] = None  # Use appropriate datetime type 

class EmailVerification(SQLModel, table=True):
    __tablename__ = "email_verifications"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="sys_users.id")
    token: str = Field(unique=True, index=True)
    is_used: bool = Field(default=False)
    created_at: Optional[str] = None  # Use appropriate datetime type if needed
    expires_at: Optional[str] = None  # Use appropriate datetime type if needed
    type:str = Field(default="email_verification")

    










