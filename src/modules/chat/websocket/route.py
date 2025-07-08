from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException, status
from src.app import app
from src.modules.chat.websocket.connection_manager import rooms, Room
import json
from src.tasks import save_messages
from src.modules.chat.models.message import Message
from src.common.dependencies import get_user_by_token

@app.websocket("/ws/{conversation_id}")
async def ws_room(websocket: WebSocket, conversation_id: int,token:str = Query(None)):
    # Get or create the room for this conversation
    role = 'agent'

    room = rooms.setdefault(conversation_id, Room())

    await room.connect(websocket, role)

    user_id = None

    if token:
        user = get_user_by_token(token)
        if not user:
            await websocket.close(code=4401)
            return
        role = 'user'
        user_id = user.id


    try:
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)
           
            if data.get('type') =='message':
                save_messages.delay(
                conversation_id=conversation_id,
                data={
                    "message":data.get('message')
                },
                user_id=user_id)
            await room.broadcast(role, data)

    except WebSocketDisconnect:
        room.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        room.disconnect(websocket)
