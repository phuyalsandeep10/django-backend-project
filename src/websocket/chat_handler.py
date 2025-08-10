import json
import asyncio
import socketio
from src.models import Message, MessageAttachment, Conversation, User, Customer
from src.common.dependencies import get_user_by_token
from src.config.broadcast import broadcast
import aioredis
from src.config.settings import settings

REDIS_URL = settings.REDIS_URL

chat_namespace = "/chat"

# Redis keys
REDIS_ROOM_KEY = "chat:room:"      # chat:room:{conversation_id} -> set of sids
REDIS_SID_KEY = "chat:sid:"        # chat:sid:{sid} -> conversation_id


# Redis helper
async def get_redis():
    return await aioredis.from_url(REDIS_URL, decode_responses=True)


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


class ChatNamespace(socketio.AsyncNamespace):
    receive_message = "recieve-message"
    receive_typing = "typing"
    stop_typing = "stop-typing"
    message_seen = "message_seen"
    chat_online = "chat_online"
    

    async def _notify_to_customers(self, org_id:int):
        await broadcast.publish(
            channel=f"ws:{org_id}:customer_sids",
            message=json.dumps({
                "event": self.chat_online,
                "mode": "online"
            })
        )
    
    async def _notify_to_users(self, org_id:int):
        await broadcast.publish(
            channel=f"ws:{org_id}:user_sids",
            message=json.dumps({
                "event": self.chat_online,
                "mode": "online"
            })
        )

    async def on_connect(self, sid, environ, auth):
        
        if not auth:
            return False
        
        token = auth.get("token")
        redis = await get_redis()

        # user connection
        if token:
            user = await get_user_by_token(token)
            if not user:
                return False
            organization_id = user.attributes.get("organization_id")
            if not organization_id:
                return False
            
            await redis.sadd(f"ws:{organization_id}:user_sids:{user.id}", sid)
            await redis.set(f"ws:{organization_id}:sid_user:{sid}", user.id)

            # notify customers in the same workspace that a user has connected
            await self._notify_to_customers(organization_id)
            print(f"User {user.id} connected with sid {sid} in workspace {organization_id}")
        
        # customer connection
        customer_id = auth.get("customer_id")
        conversation_id = auth.get("conversation_id")
        organization_id = auth.get("organization_id")

        if not conversation_id or not customer_id or not organization_id:
            return False

        await redis.sadd(f"ws:{organization_id}:conversation_sids:{conversation_id}", sid)
        await redis.set(f"ws:{organization_id}:sid_conversation:{sid}", conversation_id)

        # notify users in the same workspace that a customer has connected
        await self._notify_to_users(organization_id)

    async def on_message(self, sid, data):
        redis = await get_redis()
        conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
        if not conversation_id:
            return

        await broadcast.publish(
            channel=get_room_channel(conversation_id),
            message=json.dumps({
                "event": self.receive_message,
                "sid": sid,
                "message": data.get("message"),
                "uuid": data.get("uuid"),
                "seen": data.get("seen"),
                "user_id": data.get("user_id"),
                "files": data.get("files", [])
            })
        )

        await save_message_db(
            conversation_id=int(conversation_id),
            data=data,
            user_id=data.get("user_id")
        )

    async def on_message_seen(self, sid, data):
        redis = await get_redis()
        conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
        if not conversation_id:
            return

        await broadcast.publish(
            channel=get_room_channel(conversation_id),
            message=json.dumps({
                "event": self.message_seen,
                "sid": sid,
                "uuid": data.get("uuid")
            })
        )

    async def on_typing(self, sid, data):
        redis = await get_redis()
        conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
        if not conversation_id:
            return

        await broadcast.publish(
            channel=get_room_channel(conversation_id),
            message=json.dumps({
                "event": self.receive_typing,
                "sid": sid,
                "message": data.get("message", ""),
                "mode": data.get("mode", "typing")
            })
        )

    async def on_stop_typing(self, sid):
        redis = await get_redis()
        conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
        if not conversation_id:
            return

        await broadcast.publish(
            channel=get_room_channel(conversation_id),
            message=json.dumps({
                "event": self.stop_typing,
                "sid": sid,
                "mode": "stop-typing"
            })
        )

    async def on_disconnect(self, sid):
        redis = await get_redis()
        conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
        if conversation_id:
            await redis.srem(f"{REDIS_ROOM_KEY}{conversation_id}", sid)
            await redis.delete(f"{REDIS_SID_KEY}{sid}")
            print(f"❌ Disconnected {sid} from conversation {conversation_id}")


# Redis subscription listener
async def redis_listener(sio: socketio.AsyncServer):
    async with broadcast.subscribe("*") as subscriber:
        async for event in subscriber:
            payload = json.loads(event.message)
            event_type = payload["event"]
            conversation_id = None
            sid = payload.get("sid")

            if sid:
                redis = await get_redis()
                conversation_id = await redis.get(f"{REDIS_SID_KEY}{sid}")
                if conversation_id:
                    sids = await redis.smembers(f"{REDIS_ROOM_KEY}{conversation_id}")
                    for target_sid in sids:
                        if target_sid != sid:
                            await sio.emit(event_type, payload, room=target_sid, namespace=chat_namespace)


# Startup/shutdown hooks
@app.on_event("startup")
async def startup():
    await broadcast.connect()
    asyncio.create_task(redis_listener(sio))

@app.on_event("shutdown")
async def shutdown():
    await broadcast.disconnect()
