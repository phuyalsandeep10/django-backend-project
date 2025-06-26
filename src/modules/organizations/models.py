from src.common.models import CommonModel
from sqlmodel import  Field, Relationship, SQLModel, Session, select
from typing import Optional,List
from sqlalchemy.orm import joinedload
from src.config.database import engine
import sqlalchemy as sa



class Organization(CommonModel,table=True):
    __tablename__ = "sys_organizations"
    name: str = Field( max_length=255, index=True)
    description: str = Field(default=None, max_length=500, nullable=True)
    slug: str = Field(default=None, max_length=255, nullable=False, index=True)
    logo: str = Field(default=None, max_length=255, nullable=True)
    website: str = Field(default=None, max_length=255, nullable=True)
    members: list["OrganizationMember"] = Relationship(back_populates="organization")
    
    @classmethod
    def get_orgs_by_user_id(cls, user_id: int):
        with Session(engine) as session:
            statement = select(cls).join(OrganizationMember).where(OrganizationMember.user_id == user_id)
            return session.exec(statement).all()
        

class OrganizationRole(CommonModel, table=True):
    __tablename__ = "sys_organization_roles"
    name: str = Field(max_length=255, index=True)
    description: str = Field(default=None, max_length=500, nullable=True)
    identifier: str = Field(default=None, max_length=500, nullable=False, index=True)
    organization_id: int = Field(foreign_key="sys_organizations.id", nullable=False)


class OrganizationMember(CommonModel, table=True):
    __tablename__ = "sys_organization_members"
    user_id: int = Field(foreign_key="sys_users.id", nullable=False)
    organization_id: int = Field(foreign_key="sys_organizations.id", nullable=False)
    
    is_owner: bool = Field(default=False)
    organization: Optional[Organization] = Relationship(back_populates="members")

class OrganizationMemberRole(CommonModel, table=True):
    __tablename__ = "sys_organization_member_roles"
    member_id: int = Field(foreign_key="sys_organization_members.id", nullable=False)
    role_id: int = Field(foreign_key="sys_organization_roles.id", nullable=False)
    organization_id: int = Field(foreign_key="sys_organizations.id", nullable=False)




class OrganizationInvitation(CommonModel, table=True):
    __tablename__ = "sys_organization_invitations"
    email: str = Field(max_length=255, index=True)
    organization_id: int = Field(foreign_key="sys_organizations.id", nullable=False)
    
    invited_by_id: int = Field(foreign_key="sys_users.id", nullable=False)
    token: str = Field(max_length=255, nullable=False, unique=True)
    status: str = Field(default="pending", max_length=50, nullable=False)

    role_ids: list[int] = Field(default_factory=list, sa_column=sa.Column(sa.JSON))

  # e.g., pending, accepted, declined



class OrganizationSettings(CommonModel, table=True):
    __tablename__ = "sys_organization_settings"
    organization_id: int = Field(foreign_key="sys_organizations.id", nullable=False)
    key: str = Field(max_length=255, index=True)
    value: str = Field(max_length=500, nullable=True)
    description: str = Field(default=None, max_length=500, nullable=True)




