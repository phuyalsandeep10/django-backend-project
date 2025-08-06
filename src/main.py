import logging

from apscheduler.triggers.interval import IntervalTrigger
from fastapi import Request, WebSocket
from fastapi.responses import HTMLResponse

from src.app import app
from src.config.broadcast import broadcast
from src.config.scheduler import scheduler, start_scheduler
from src.routers import add_routers
from src.socket_config import socket_app
from src.tasks.sla_task import check_sla_breach
from src.utils.exceptions import add_exceptions_handler

# custom exceptions
add_exceptions_handler(app)

# logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s -%(name)s - %(message)s"
)


# apscheduler configuration
@app.on_event("startup")
async def startup_event():
    start_scheduler()
    scheduler.add_job(check_sla_breach, IntervalTrigger(seconds=10))


# adding routers
add_routers(app)


async def sender(websocket: WebSocket, room: str):
    async with broadcast.subscribe(channel=f"room_{room}") as subscriber:
        async for event in subscriber:
            await websocket.send_text(event.message)


async def receiver(websocket: WebSocket, room: str):
    async for message in websocket.iter_text():
        await broadcast.publish(channel=f"room_{room}", message=message)


# @app.websocket("/{room}")
# async def websocket_chat(websocket: WebSocket, room: str):
#     await websocket.accept()
#     await run_until_first_complete(
#         (receiver, {"websocket": websocket, "room": room}),
#         (sender, {"websocket": websocket, "room": room}),
#     )


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/chat")
async def get(request: Request):
    with open("src/templates/index.html") as f:
        return HTMLResponse(f.read())


@app.get("/health")
def read_items():
    return "Health check OK"
