from src.common.models import CommonModel



class Customer(CommonModel,table=True):
    __tablename__ = "org_customers"
    name: str = Field(max_length=255, index=True,nullable=True)
    description: str = Field(default=None, max_length=500, nullable=True)
    organization_id: int = Field(foreign_key="sys_organizations.id", nullable=False)
    organization: Optional["Organization"] = Relationship(back_populates="customers")
    conversations: list["Conversation"] = Relationship(back_populates="customer")

    phone: str = Field(max_length=255, index=True,nullable=True)
    email: str = Field(max_length=255, index=True,nullable=True)

    ip_address: str = Field(max_length=255, index=True,nullable=True)
    
