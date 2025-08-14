from src.models import Message, MessageAttachment, Conversation


def customer_notification_group(org_id: int):
    return f"org-{org_id}-customers"


def user_notification_group(org_id: int):
    return f"org-{org_id}-users"


def conversation_group(conversationId: int):
    return f"conversation-{conversationId}"

def get_room_channel(conversation_id: int) -> str:
    print(f"get_room_channel called with conversation_id: {conversation_id}")
    return f"conversation-{conversation_id}"





async def save_message_db(conversation_id: int, data: dict, user_id=None):
    conversation = await Conversation.get(conversation_id)
    if not conversation:
        return None

    replyId = data.get("reply_id")
    msg = await Message.create(
        conversation_id=conversation_id,
        content=data.get("message"),
        customer_id=conversation.customer_id,
        user_id=user_id,
        reply_to_id=replyId,
    )
    for file in data.get("files", []):
        await MessageAttachment.create(
            message_id=msg.id,
            file_url=file.get("url"),
            file_name=file.get("file_name"),
            file_type=file.get("file_type"),
            file_size=file.get("file_size"),
        )
    return msg