import secrets

from fastapi import HTTPException, status
from kombu import message
from sqlalchemy.orm import selectinload
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from src.common.dependencies import get_user_by_token
from src.modules.auth.models import User
from src.modules.ticket.models.contact import Contact
from src.modules.ticket.models.sla import TicketSLA
from src.modules.ticket.models.status import TicketStatus
from src.modules.ticket.models.ticket import Ticket
from src.modules.ticket.schemas import CreateTicketSchema
from src.tasks.ticket_task import send_ticket_verification_email
from src.utils.response import CustomResponse as cr


class TicketServices:

    async def create_ticket(self, payload: CreateTicketSchema, user):
        """
        Create ticket for the organization
        """
        try:
            user_id = user.id
            data = dict(payload)
            data["created_by_id"] = user_id
            data["organization_id"] = user.attributes.get("organization_id")
            # for getting the default ticket status set by the organization
            sts = await TicketStatus.find_one(
                where={
                    "is_default": True,
                    "organization_id": data["organization_id"],
                }
            )
            if not sts:
                raise HTTPException(
                    status_code=500, detail="Ticket default status has not been set yet"
                )
            data["status_id"] = sts.id
            if data["assignees"] is not None:
                users = []
                for assigne_id in data["assignees"]:
                    usr = await User.find_one(where={"id": assigne_id})
                    users.append(usr)

                data["assignees"] = users

            del data["assignees"]  # not assigning None to the db
            # generating the confirmation token using secrets
            data["confirmation_token"] = secrets.token_hex(32)
            tick = await Ticket.find_one(
                where={
                    "id": (await Ticket.create(**dict(data))).id,
                    "organization_id": data["organization_id"],
                },
                related_items=[selectinload(Ticket.customer)],
            )

            if not tick:
                return cr.error(
                    message="Error while processing ticket",
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                )

            send_ticket_verification_email.delay(
                email=(
                    tick.customer.email
                    if tick.customer is not None
                    else tick.customer_email
                ),
                token=data["confirmation_token"],
                ticket_id=tick.id,
            )

            return cr.success(
                status_code=status.HTTP_201_CREATED,
                message="Successfully created a ticket",
            )
        except Exception as e:
            print(e)
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Error while creating a ticket",
            )

    async def list_tickets(self, user):
        """
        List all the tickets of the user organization
        """
        try:
            all_tickets = await Ticket.filter(
                where={"organization_id": user.attributes.get("organization_id")},
                related_items=[
                    selectinload(Ticket.sla),
                    selectinload(Ticket.assignees),
                    selectinload(Ticket.priority),
                    selectinload(Ticket.status),
                    selectinload(Ticket.customer),
                    selectinload(Ticket.created_by),
                    selectinload(Ticket.department),
                ],
            )
            tickets = [ticket.to_dict() for ticket in all_tickets]
            return cr.success(
                status_code=status.HTTP_200_OK,
                message="Successfully listed all tickets",
                data=tickets,
            )
        except Exception as e:
            print(e)
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Error while listing  tickets",
            )

    async def get_ticket(self, ticket_id: int, user):
        """
        List the particular ticket of the organization by id
        """
        try:
            organization_id = user.attributes.get("organization_id")
            ticket = await Ticket.find_one(
                where={"id": ticket_id, "organization_id": organization_id},
                options=[
                    selectinload(Ticket.sla),
                    selectinload(Ticket.assignees),
                    selectinload(Ticket.priority),
                    selectinload(Ticket.status),
                    selectinload(Ticket.customer),
                    selectinload(Ticket.created_by),
                    selectinload(Ticket.department),
                ],
            )
            if ticket is None:
                return cr.error(message="Not found")
            return cr.success(
                status_code=status.HTTP_200_OK,
                message="Successfully listed the ticket",
                data=ticket.to_dict() if ticket else [],
            )
        except Exception as e:
            print(e)
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Error while listing ticket",
            )

    async def delete_ticket(self, ticket_id: int, user):
        try:
            await Ticket.delete(
                where={
                    "id": ticket_id,
                    "organization_id": user.attributes.get("organization_id"),
                }
            )
            return cr.success(
                status_code=status.HTTP_200_OK,
                message="Successfully deleted the ticket",
            )
        except Exception as e:
            print(e)
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Error while deleting the tickets",
            )

    async def confirm_ticket(self, ticket_id: int, token: str, user):
        try:
            ticket = await Ticket.find_one(where={"id": ticket_id})
            if ticket is None:
                return cr.error(message="Ticket with this id not found")
            # to find which is the open status category status defined the organization it could be in-progress, or open,ongoing
            open_status_category = await TicketStatus.find_one(
                where={
                    "organization_id": user.attributes.get("organization_id"),
                    "status_category": "open",
                }
            )
            if open_status_category is None:
                return cr.error(
                    message="Open status category is not set in the ticket status"
                )
            if ticket.confirmation_token == token:
                ticket.status_id = open_status_category.id
                return cr.error(
                    message="Your ticket has been activated.", data=ticket.to_dict()
                )

            return cr.error(message="Invalid confirmation token")

        except Exception as e:
            print(e)
            return cr.error(message="Invalid confirmation token")


ticket_services = TicketServices()
