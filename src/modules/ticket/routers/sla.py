from typing import List

from fastapi import APIRouter, Depends

from src.common.dependencies import get_current_user
from src.modules.ticket.schemas import CreateSLASchema, EditTicketSLASchema, SLAOut
from src.modules.ticket.services.sla import sla_service
from src.utils.response import CustomResponseSchema

router = APIRouter()


@router.post(
    "/sla",
    summary="Creates new Service Level agreement",
    response_model=CustomResponseSchema,
)
async def register_sla(payload: CreateSLASchema):
    """
    Registers the ticket sla
    """
    return await sla_service.register_sla(payload)


@router.get(
    "/sla",
    summary="List all Service Level agreements",
    response_model=CustomResponseSchema[List[SLAOut]],
)
async def get_all():
    """
    list all service level agreements
    """
    return await sla_service.list_slas()


@router.get(
    "/sla/{sla_id}", summary="Get a SLA", response_model=CustomResponseSchema[SLAOut]
)
async def get_sla(sla_id: int):
    """
    List the sla by id
    """
    return await sla_service.get_sla(sla_id)


@router.patch(
    "/sla/{sla_id}", summary="Edit SLA", response_model=CustomResponseSchema[SLAOut]
)
async def edit_sla(sla_id: int, payload: EditTicketSLASchema):
    """
    Edit the sla by id
    """
    return await sla_service.edit_sla(sla_id, payload)


@router.delete(
    "/sla/{sla_id}", summary="Delete a SLA", response_model=CustomResponseSchema
)
async def delete_sla(sla_id: int):
    """
    delete sla by id
    """
    return await sla_service.delete_sla(sla_id)
