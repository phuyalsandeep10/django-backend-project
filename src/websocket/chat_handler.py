import json
import asyncio
import socketio
from src.common.context import organization_id_ctx
from src.models import Message, MessageAttachment, Conversation, User, Customer
from src.common.dependencies import get_user_by_token

# from src.config.broadcast import broadcast  # Replaced with direct Redis pub/sub
import redis.asyncio as redis
from src.config.settings import settings

REDIS_URL = settings.REDIS_URL

chat_namespace = "/chat"

# Redis keys
REDIS_ROOM_KEY = "chat:room:"  # chat:room:{conversation_id} -> set of sids
REDIS_SID_KEY = "chat:sid:"  # chat:sid:{sid} -> conversation_id


# Redis helper
async def get_redis():
    return redis.from_url(REDIS_URL, decode_responses=True)


async def redis_publish(channel: str, message: str):
    """Direct Redis pub/sub publish - more reliable than broadcaster library"""
    redis_client = await get_redis()
    try:
        result = await redis_client.publish(channel, message)
        print(f"📡 Published to Redis channel '{channel}': {result} subscribers")
        return result
    except Exception as e:
        print(f"❌ Redis publish failed: {e}")
        return 0
    finally:
        await redis_client.aclose()


def get_room_channel(conversation_id: int) -> str:
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


def customer_notification_group(org_id: int):
    return f"org-{org_id}-customers"


def user_notification_group(org_id: int):
    return f"org-{org_id}-users"


def conversation_group(conversationId: int):
    return f"org-conversation-${conversationId}"


class ChatNamespace(socketio.AsyncNamespace):
    receive_message = "receive-message"
    receive_typing = "typing"
    stop_typing = "stop-typing"
    message_seen = "message_seen"
    chat_online = "chat_online"
    customer_land = "customer_land"

    def __init__(self):
        super().__init__("/chat")
        self.rooms = {}

    async def _notify_to_customers(self, org_id: int):
        await redis_publish(
            channel=f"ws:{org_id}:customer_notification",
            message=json.dumps(
                {"event": self.chat_online, "mode": "online", "organization_id": org_id}
            ),
        )

    async def _notify_to_users(self, org_id: int):
        print(f"notify users in the same workspace that a customer has connected")
        await redis_publish(
            channel=f"ws:{org_id}:user_notification",
            message=json.dumps(
                {"event": self.customer_land, "mode": "online", "organization_id": org_id}
            ),
        )

    async def _join_org_user_group(self, org_id: int, sid: int):
        print(f"join room name {user_notification_group(org_id)} and sid {sid}")
        await self.enter_room(sid=sid, room=user_notification_group(org_id))

    async def _join_org_customer_group(self, org_id: int, sid: int):
        self.enter_room(sid=sid, room=customer_notification_group(org_id))

    async def _join_conversation(self, conversation_id: int, sid: int):
        self.enter_room(sid=sid, room=conversation_group(conversation_id))
    
    async def _leave_user_group(self, org_id: int, sid: int):
        self.leave_room(sid=sid, room=user_notification_group(org_id))
    
    async def _leave_customer_group(self, org_id: int, sid: int):
        self.leave_room(sid=sid, room=customer_notification_group(org_id))
    
  

    async def on_connect(self, sid, environ, auth):
        # print(f"🔌 Socket connection attempt: {sid}")
        # print(f"🔑 Auth data: {auth}")

        if not auth:
            print("No auth data provided")
            return False

        redis = await get_redis()
        token = auth.get("token")

        # Handle user connection (with token)
        if token:
            user = await get_user_by_token(token)
            if not user:
                print("Invalid token provided")
                return False

            organization_id = user.attributes.get("organization_id")

            if not organization_id:
                print("User has no organization_id")
                return False

            await redis.sadd(f"ws:{organization_id}:user_sids:{user.id}", sid)
            await redis.set(f"ws:{organization_id}:sid_user:{sid}", user.id)

            await self._join_org_user_group(organization_id, sid)
            # notify customers in the same workspace that a user has connected
            await self._notify_to_customers(organization_id)
            print(
                f"User {user.id} connected with sid {sid} in workspace {organization_id}"
            )
            return True

        # Handle customer connection (without token)
        customer_id = auth.get("customer_id")
        conversation_id = auth.get("conversation_id")
        organization_id = auth.get("organization_id")

   

        if not conversation_id or not customer_id:
            print(
                f"❌ Missing customer connection data: customer_id={customer_id}, conversation_id={conversation_id}"
            )
            return False

        # For customer connections, we'll use organization_id = 1 as default if not provided
        if not organization_id:
            organization_id = 1
            print(f"Using default organization_id: {organization_id}")

        await redis.sadd(
            f"ws:{organization_id}:conversation_sids:{conversation_id}", sid
        )
        await redis.set(f"ws:{organization_id}:sid_conversation:{sid}", conversation_id)

        # Maintain conversation membership for cross-instance message fanout
        await redis.sadd(f"{REDIS_ROOM_KEY}{conversation_id}", sid)
        await redis.set(f"{REDIS_SID_KEY}{sid}", conversation_id)

        # notify users in the same workspace that a customer has connected
        await self._notify_to_users(organization_id)
        await self._join_org_customer_group(organization_id, sid)
        # notify users with a specific customer landing event
        channel = f"ws:{organization_id}:user_notification"
    

        print(f"✅ Published customer_land event to {channel}")

      

        return True

    async def on_message(self, sid, data):
        redis = await get_redis()
        conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
        if not conversation_id:
            return

        await redis_publish(
            channel=get_room_channel(conversation_id),
            message=json.dumps(
                {
                    "event": self.receive_message,
                    "sid": sid,
                    "message": data.get("message"),
                    "uuid": data.get("uuid"),
                    "seen": data.get("seen"),
                    # "status":data.get('status'),#delivered, pending and seen
                    "user_id": data.get("user_id"),
                    "files": data.get("files", []),
                }
            ),
        )

        await save_message_db(
            conversation_id=int(conversation_id), data=data, user_id=data.get("user_id")
        )

    async def on_message_seen(self, sid, data):
        redis = await get_redis()
        conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
        if not conversation_id:
            return

        await redis_publish(
            channel=get_room_channel(conversation_id),
            message=json.dumps(
                {"event": self.message_seen, "sid": sid, "uuid": data.get("uuid")}
            ),
        )

    async def on_typing(self, sid, data):
        redis = await get_redis()
        conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
        if not conversation_id:
            return

        await redis_publish(
            channel=get_room_channel(conversation_id),
            message=json.dumps(
                {
                    "event": self.receive_typing,
                    "sid": sid,
                    "message": data.get("message", ""),
                    "mode": data.get("mode", "typing"),
                }
            ),
        )

    async def on_stop_typing(self, sid):
        redis = await get_redis()
        conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
        if not conversation_id:
            return

        await redis_publish(
            channel=get_room_channel(conversation_id),
            message=json.dumps(
                {"event": self.stop_typing, "sid": sid, "mode": "stop-typing"}
            ),
        )

    async def on_disconnect(self, sid,auth):
        customer_id = auth.get('customer_id')
        conversation_id = auth.get('conversation_id')
        organization_id = auth.get('organization_id')
        user_id = auth.get('user_id')
        if customer_id:
            await redis.srem(f"ws:{organization_id}:conversation_sids:{conversation_id}", sid)
            await redis.delete(f"ws:{organization_id}:sid_conversation:{sid}")
            await self._leave_customer_group(organization_id, sid)
        if user_id:
            await redis.srem(f"ws:{organization_id}:user_sids:{user_id}", sid)
            await redis.delete(f"ws:{organization_id}:sid_user:{sid}")
            await self._leave_user_group(organization_id, sid)

            
        redis = await get_redis()
        conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
        if conversation_id:
            await redis.srem(f"{REDIS_ROOM_KEY}{conversation_id}", sid)
            await redis.delete(f"{REDIS_SID_KEY}{sid}")
            print(f"❌ Disconnected {sid} from conversation {conversation_id}")
