from src.config.celery import celery_app
from typing import Optional
from src.modules.chat.models.message import Message
from src.modules.chat.models.conversation import Conversation


@celery_app.task
def save_messages(conversation_id: int, data:dict,user_id:Optional[int]=None):
    print("saving message in queue")
    conversation = Conversation.get(conversation_id)
    customer_id = conversation.customer_id
    if user_id:
        customer_id = None

    message = Message.create(
        conversation_id=conversation_id,
        content=data.get('message'),
        customer_id=customer_id,
        user_id=user_id
    )

    