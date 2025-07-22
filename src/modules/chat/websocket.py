from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException, status
from src.app import app

import json
from src.tasks import save_messages
from src.models import Message
from src.common.dependencies import get_user_by_token
from src.config.broadcast import broadcast
from fastapi.concurrency import run_until_first_complete
from typing import Optional
from src.socket_config import sio


chat_namespace = "/chat"

def get_room(conversationId: int):
    return f"conversation-{conversationId}"

async def ws_send(conversation_id: int, user_id: Optional[int] = None):
    room = get_room(conversationId=conversation_id)
    try:
        room = get_room(conversation_id)
        async with broadcast.subscribe(channel=room) as subscriber:
            async for event in subscriber:
                # data = json.loads(event.message)
                # if data.get("type") == "message":
                #     print("save messages in redis subscriber")
                #     save_messages.delay(
                #         conversation_id=conversation_id,
                #         data={"message": data.get("message")},
                #         user_id=user_id,
                #     )

                await sio.emit(
                    "response", {"data": "Chat received"}, room=room, namespace=chat_namespace
                )
    except Exception as e:
        print(f"Exception in ws_send: {e}")


async def ws_recv(ws: WebSocket, conversation_id: int, user_id: Optional[int] = None):
    try:
        room = get_room(conversation_id)
        async for text in ws.iter_text():
            await broadcast.publish(channel=room, message=text)
    except Exception as e:
        print(f"Exception in ws_recv: {e}")

# class ChatNamespace(socketio.AsyncNamespace):
#     def __init__(self):
#         super().__init__("/chat")
#     async def on_connect(self, sid, environ, auth):
#         print("Chat connected:", sid)
#     async def on_message(self, sid, data):
#         print("Chat message:", data)
#         await self.emit("response", {"data":"OK"}, room=sid)
#     def on_disconnect(self, sid):
#         print("Chat disconnect:", sid)
    
# sio.register_namespace(ChatNamespace())

# @sio.event(namespace=chat_namespace)
# async def connect(sid, environ, auth):
 
#     print(f"Chat route client connected: {sid}")
#     print("auth ", auth)
    


# # Similarly, define events for each namespace
# @sio.event(namespace=chat_namespace)
# async def message(sid, data):
#     print(f"Chat message: {data}")
#     await sio.emit(
#         "response", {"data": "Chat received"}, room=sid, namespace=chat_namespace
#     )


# @sio.event(namespace=chat_namespace)
# async def disconnect(sid):
#     print(f"Client disconnected: {sid}")







# @app.websocket("/ws/{conversation_id}")
# async def ws_room(websocket: WebSocket, conversation_id: int, token: str = Query(None)):
#     # Get or create the room for this conversation
#     role = "agent"

#     room = rooms.setdefault(conversation_id, Room())

#     await room.connect(websocket, role)

#     user_id = None

#     if token:
#         user = get_user_by_token(token)
#         if not user:
#             await websocket.close(code=4401)
#             return
#         role = "user"
#         user_id = user.id

#     try:
#         await run_until_first_complete(
#             (
#                 ws_recv,
#                 {
#                     "ws": websocket,
#                     "conversation_id": conversation_id,
#                     "user_id": user_id,
#                 },
#             ),
#             (
#                 ws_send,
#                 {
#                     "ws": websocket,
#                     "conversation_id": conversation_id,
#                     "user_id": user_id,
#                 },
#             ),
#         )
#         # while True:
#         #     data = await websocket.receive_text()
#         #     data = json.loads(data)

#         #     if data.get('type') =='message':
#         #         print("save messages in websocket")
#         #         save_messages.delay(
#         #         conversation_id=conversation_id,
#         #         data={
#         #             "message":data.get('message')
#         #         },
#         #         user_id=user_id)
#         #     await room.broadcast(role, data)

#     except WebSocketDisconnect:
#         room.disconnect(websocket)
#     except Exception as e:
#         print(f"WebSocket error: {e}")
#         room.disconnect(websocket)
