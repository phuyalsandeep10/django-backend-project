# chat_manager.py
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict, deque
from typing import Dict, Set, Deque, Optional

class ChatManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.assignments: Dict[str, str] = {}            # room_id → agent_id
        self.available_agents: Deque[str] = deque()      # round-robin
        self.ws_user: Dict[WebSocket, str] = {}          # websocket → user_id
        self.ws_role: Dict[WebSocket, str] = {}          # websocket → "agent"/"customer"

    async def connect(self, room: str, user_id: str, role: str, ws: WebSocket):
        await ws.accept()
        self.rooms[room].add(ws)
        self.ws_user[ws] = user_id
        self.ws_role[ws] = role
        
        if role == "agent" and user_id not in self.available_agents:
            self.available_agents.append(user_id)

    def disconnect(self, room: str, ws: WebSocket):
        self.rooms[room].discard(ws)
        user = self.ws_user.pop(ws, None)
        role = self.ws_role.pop(ws, None)
        if role == "agent" and user in self.available_agents:
            self.available_agents.remove(user)

            
        if room in self.assignments and self.assignments[room] == user:
            del self.assignments[room]

        if not self.rooms[room]:
            del self.rooms[room]

    def assign_agent(self, room: str, agent_id: Optional[str] = None):
        if agent_id:
            self.assignments[room] = agent_id
        else:
            # auto assign via round robin
            if self.available_agents:
                agent = self.available_agents[0]
                self.available_agents.rotate(-1)
                self.assignments[room] = agent

    async def broadcast_message(self, room: str, sender_ws: WebSocket, payload: dict):
        sender = self.ws_user.get(sender_ws)
        assigned = self.assignments.get(room)
        for ws in self.rooms.get(room, []):
            role = self.ws_role.get(ws)
            user = self.ws_user.get(ws)
            # customer always receives
            if role == "customer":
                await ws.send_json(payload)
            elif role == "agent":
                # if assigned, only that agent gets it; else broadcast to all agents
                if assigned:
                    if user == assigned:
                        await ws.send_json(payload)
                else:
                    await ws.send_json(payload)

    async def broadcast_typing(self, room: str, sender_ws: WebSocket, status: bool):
        payload = {
            "type": "typing",
            "user": self.ws_user.get(sender_ws),
            "status": status
        }
        await self.broadcast_message(room, sender_ws, payload)
