from src.common.models import CommonModel



class Message(CommonModel,table=True):
    __tablename__ = "org_messages"
    conversation_id: int = Field(foreign_key="org_conversations.id", nullable=False)
    conversation: Optional[Conversation] = Relationship(back_populates="messages")
    content: str = Field(max_length=255, index=True)
    sender_type: str = Field(max_length=255, index=True)
    customer_id: int = Field(foreign_key="org_customers.id", nullable=False)
    customer: Optional[Customer] = Relationship(back_populates="messages")
    sender_id: int = Field(foreign_key="org_conversation_members.id", nullable=True)
    sender: Optional["ConversationMember"] = Relationship(back_populates="messages")

    feedback: str = Field(max_length=255, index=True,nullable=True)

    attachments: list["MessageAttachment"] = Relationship(back_populates="message")

class MessageAttachment(CommonModel,table=True):
    __tablename__ = "org_message_attachments"
    message_id: int = Field(foreign_key="org_messages.id", nullable=False)
    message: Optional[Message] = Relationship(back_populates="attachments")
    file_name: str = Field(max_length=255)
    file_type: str = Field(max_length=255)
    file_size: int = Field(index=True)
    file_url: str = Field(max_length=255)


