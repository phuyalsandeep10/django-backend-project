from fastapi import FastAPI, WebSocket, WebSocketDisconnect,Query
from fastapi.responses import HTMLResponse

from typing import Dict, Set, Optional
from src.app import app
from fastapi.concurrency import run_until_first_complete
from src.config.broadcast import broadcast
import json

def get_channel_name(conversation_id:str):
    return f"conversation_{conversation_id}"

async def receiver(websocket: WebSocket, conversation_id: str):
    async for text in websocket.iter_text():
        data = json.loads(text)  # {"type":"message"/"typing", ...}
        print(f"data {data}")
        try:
        
        # Broadcast to all subscribers in this room
            await broadcast.publish(
            channel=get_channel_name(conversation_id),
            message=json.dumps({
                "type": data["type"],
                "user": data.get("user"),
                "message": data.get("message", "")
            }))
            
        except Exception as e:
            print("except error ",e)

        # Only persist in DB if it's a message—skip typing events
        # if data["type"] == "message":
        #     with Session(engine) as session:
        #         session.add(Message(room_id=room_id, user_id=..., content=data["message"]))
        #         session.commit()

async def sender(websocket: WebSocket, conversation_id: str):
    print("conversation id: ", conversation_id)
    try:
        async with broadcast.subscribe(get_channel_name(conversation_id)) as subscriber:
            async for message in subscriber:
                print("🔔 Received:", message.message)
    except Exception as e:
        print("Sender exception:", e)


@app.websocket("/ws/{conversation_id}")
async def ws_room(
    websocket: WebSocket,
    conversation_id: str,
    role=Query(...),
    token=Query(None)

):

    if role =='staff':
        pass
    
    await websocket.accept()
    await receiver(websocket=websocket,conversation_id=conversation_id)
    await sender(websocket=websocket,conversation_id=conversation_id)
    # await run_until_first_complete(
    #     (receiver, {"websocket": websocket, "conversation_id": conversation_id}),
    #     (sender, {"websocket": websocket, "conversation_id": conversation_id})
    # )