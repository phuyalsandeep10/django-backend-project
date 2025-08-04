import logging
from typing import List

from kombu import message
from starlette.status import HTTP_400_BAD_REQUEST

from src.modules.auth.models import User
from src.modules.ticket.models import TicketStatus
from src.modules.ticket.schemas import (
    CreateTicketStatusSchema,
    EditTicketStatusSchema,
    TicketStatusOut,
)
from src.utils.response import CustomResponse as cr

logger = logging.getLogger(__name__)


class TicketStatusService:

    async def list_ticket_status(self, user):
        """
        List all the ticket status on the basis of the organization
        """
        try:
            ticket_status = await TicketStatus.filter()
            # if there is none of them, then list the default ones
            if len(ticket_status) == 0:
                payload = await self.get_default_status()
                return cr.success(message="Successfully listed status", data=payload)
            payload = [status.to_json(TicketStatusOut) for status in ticket_status]
            return cr.success(message="Successfully listed status", data=payload)
        except Exception as e:
            logger.exception(e)
            return cr.error(message="Error while listing status")

    async def create_ticket_status(self, payload: List[CreateTicketStatusSchema], user):
        """
        create single status or list of ticket status at the same time
        """
        try:
            for d in payload:
                data = d.model_dump()
                record = await TicketStatus.find_one(where={"name": data["name"]})
                if not record:
                    await TicketStatus.create(**data)

            return cr.success(
                message="Successfully created ticket status", status_code=201
            )
        except Exception as e:
            logger.exception(e)
            return cr.error(message="Error while creating ticket status")

    async def get_ticket_status(self, ticket_status_id: int, user):
        """
        List particular ticket status of the organization
        """
        try:
            ticket_status = await TicketStatus.find_one(where={"id": ticket_status_id})
            if ticket_status is None:
                return cr.error(message="Not found")
            return cr.success(
                message="Successfully listed ticket status",
                data=ticket_status.to_json(TicketStatusOut) if ticket_status else None,
            )
        except Exception as e:
            logger.exception(e)
            return cr.error(message="Error while listing ticket status")

    async def delete_ticket_status(self, ticket_status_id: int, user):
        """
        Delete ticket status by id
        """
        try:
            await TicketStatus.delete(where={"id": ticket_status_id})
            return cr.success(message="Successfully deleted the ticket status")
        except Exception as e:
            logger.exception(e)
            return cr.error(message="Error while deleting the ticket status")

    async def edit_ticket_status(
        self, ticket_status_id: int, payload: EditTicketStatusSchema, user
    ):
        """
        Edit ticket status of the organization
        """
        try:
            ticket_status = await TicketStatus.find_one(
                where={
                    "id": ticket_status_id,
                }
            )
            if ticket_status is None:
                return cr.error(
                    message="Ticket Status not found", status_code=HTTP_400_BAD_REQUEST
                )

            updated_ticket_status = await TicketStatus.update(
                ticket_status.id, **payload.model_dump(exclude_none=True)
            )

            return cr.success(
                message="Successfully updated ticket status",
                data=(
                    updated_ticket_status.to_json(TicketStatusOut)
                    if updated_ticket_status
                    else None
                ),
            )
        except Exception as e:
            logger.exception(e)
            return cr.error(message="Error while editing ticket status", data=str(e))

    async def get_default_status(self):
        """
        Returns the default ticket status
        """
        default_ticket_status = await TicketStatus.filter(
            where={"organization_id": None}
        )
        payload = [status.to_json(TicketStatusOut) for status in default_ticket_status]
        return payload


ticket_status_service = TicketStatusService()
