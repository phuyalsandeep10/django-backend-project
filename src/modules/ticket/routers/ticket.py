from typing import Annotated

from fastapi import APIRouter, Header

from src.modules.ticket.schemas import CreateTicketSchema, FullCreateTicketSchema
from src.modules.ticket.services.ticket import ticket_services

router = APIRouter()


@router.post("/", summary="Creates new ticket")
async def register_ticket(
    payload: CreateTicketSchema, authorization: Annotated[str, Header()]
):
    print("Triggered")
    return await ticket_services.create_ticket(payload, authorization)


@router.get("/", summary="List all tickets")
async def list_tickets():
    return await ticket_services.list_tickets()


@router.post("/full-create", summary="Creates new ticket with full credentials")
async def register_full_ticket(
    payload: FullCreateTicketSchema, authorization: Annotated[str, Header()]
):
    return await ticket_services.create_full_ticket(payload, authorization)
