from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException, status
from src.app import app

import json
from src.tasks import save_messages
from src.models import Message
from src.common.dependencies import get_user_by_token
from src.config.broadcast import broadcast
from fastapi.concurrency import run_until_first_complete
from typing import Optional

# from src.socket_config import sio
import socketio


chat_namespace = "/chat"


def get_room(conversationId: int):
    return f"conversation-{conversationId}"


async def ws_send(conversation_id: int, user_id: Optional[int] = None):
    room = get_room(conversationId=conversation_id)
    try:
        room = get_room(conversation_id)
        async with broadcast.subscribe(channel=room) as subscriber:
            async for event in subscriber:
                pass
                # data = json.loads(event.message)
                # if data.get("type") == "message":
                #     print("save messages in redis subscriber")
                #     save_messages.delay(
                #         conversation_id=conversation_id,
                #         data={"message": data.get("message")},
                #         user_id=user_id,
                #     )

                # await sio.emit(
                #     "response", {"data": "Chat received"}, room=room, namespace=chat_namespace
                # )
    except Exception as e:
        print(f"Exception in ws_send: {e}")


async def ws_recv(ws: WebSocket, conversation_id: int, user_id: Optional[int] = None):
    try:
        room = get_room(conversation_id)
        async for text in ws.iter_text():
            await broadcast.publish(channel=room, message=text)
    except Exception as e:
        print(f"Exception in ws_recv: {e}")


rooms = {}


conversations = {}


def get_conversation(conversation_id):
    return conversations.get(conversation_id)


def create_conversation(conversation_id, customer_id):
    conversation = {"customer_id": customer_id, "online": False, "sids": []}
    conversations[conversation_id] = conversation
    return conversation


def update_conversation(conversation_id, customer_id, online):
    conversation = get_conversation(conversation_id)
    if conversation:
        conversation["online"] = online
        conversation["customer_id"] = customer_id


class ChatNamespace(socketio.AsyncNamespace):
    """WebSocket namespace for chat functionality."""

    receive_message = "recieve-message"
    receive_typing = "typing"
    stop_typing = "stop-typing"

    def __init__(self):
        super().__init__("/chat")
        self.rooms = {}

    async def on_connect(self, sid, environ, auth):
        print(f"Chat connected: {sid}")
        print("auth ", auth)
        if not auth:
            print("❌ No auth provided")
            return False
        token = auth.get("token")
        customer_id = auth.get("customer_id")
        conversation_id = auth.get("conversation_id")

        if not customer_id or not conversation_id:
            return False

        conversation = get_conversation(conversation_id)

        if not conversation:
            conversation = create_conversation(conversation_id, customer_id)

        self.rooms[sid] = conversation_id
        conversation["sids"].append(sid)
        conversation["online"] = True

        print(f"✅ Connected to /chat: {sid} (conversation_id: {conversation_id})")
        return True

    async def on_message(self, sid, data):
        conversation_id = self.rooms.get(sid)
        if not conversation_id:
            return

        conversation = get_conversation(conversation_id)

        print(f"conversation id {conversation_id} and conversation {conversation}")

        if not conversation:
            return

        for si in conversation["sids"]:

            if si == sid:
                continue

            print(f"Sending message to {si} from {sid}")

            await self.emit(
                self.receive_message,
                {
                    "message": data.get("message"),
                    "sid": sid,
                    "mode": "message",
                },
                room=si,
            )

    async def on_typing(self, sid, data):
        """Handle typing events."""
        print(f"Typing event from {sid}: {data}")
        conversation_id = self.rooms.get(sid)
        if not conversation_id:
            return

        conversation = get_conversation(conversation_id)
        if not conversation:
            return

        for si in conversation["sids"]:
            if si == sid:
                continue

            await self.emit(
                self.receive_typing,
                {
                    "message": data.get("message"),
                    "sid": sid,
                    "mode": data.get("mode", "typing"),
                },
                room=si,
            )

    async def on_stop_typing(self, sid):
        """Handle stop typing events."""
        print(f"Stop typing event from {sid}")
        conversation_id = self.rooms.get(sid)
        if not conversation_id:
            return

        conversation = get_conversation(conversation_id)
        if not conversation:
            return

        for si in conversation["sids"]:
            if si == sid:
                continue
            print(f"Stopping typing for {si} from {sid}")
            await self.emit(
                self.stop_typing,
                {
                    "message": "",
                    "sid": sid,
                    "mode": "stop-typing",
                },
                room=si,
            )

    def on_disconnect(self, sid):
        conversation_id = self.rooms.get(sid)
        if conversation_id:
            conversation = get_conversation(conversation_id)
            if conversation:
                conversation["sids"].remove(sid)
                conversation["online"] = len(conversation["sids"]) > 0
                print(f"❌ Disconnected: {sid} (conversation_id: {conversation_id})")
