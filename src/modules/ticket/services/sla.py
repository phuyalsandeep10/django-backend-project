from datetime import datetime

from fastapi import HTTPException, status
from sqlmodel import BigInteger

from src.common.dependencies import get_user_by_token
from src.modules.auth.models import User
from src.modules.ticket.models import SLA
from src.modules.ticket.models.ticket import Ticket
from src.modules.ticket.schemas import CreateSLASchema
from src.utils.response import CustomResponse as cr


class SLAServices:

    async def register_sla(self, payload: CreateSLASchema, user: User):
        try:

            user_id = user.id
            data = dict(payload)
            data["issued_by"] = user_id
            data["organization_id"] = user.attributes.get("organization_id")

            sla = await SLA.create(**data)

            if not sla:
                return cr.error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Error while registering Service Level Agreement",
                )

            return cr.success(
                status_code=status.HTTP_200_OK,
                message="Successfully registered the Service Level Agreement",
                data=sla.to_dict(),
            )
        except IndexError as e:
            print(e)
            return cr.error(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Token required in standard format",
            )

        except HTTPException:

            raise

        except Exception as e:
            print(e)
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Error while registering Service Level Agreement",
            )

    async def list_slas(self):
        try:
            sla_list = await SLA.get_all()
            slas = [s.to_dict() for s in sla_list]

            return cr.success(
                status_code=status.HTTP_200_OK,
                message="Successfully fetched all the sla",
                data=slas,
            )

        except Exception as e:
            print(e)
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Error while fetching Service Level Agreement",
            )

    async def get_sla(self, sla_id: int):
        try:
            sla = await SLA.find_one(where={"id": sla_id})

            return cr.success(
                status_code=status.HTTP_200_OK,
                message="Successfully fetched the sla",
                data=sla.to_dict(),
            )

        except Exception as e:
            print(e)
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Error while fetching Service Level Agreement",
            )

    async def delete_sla(self, sla_id: int):
        try:
            await SLA.delete(id=sla_id)
            return cr.success(
                status_code=status.HTTP_200_OK,
                message="Successfully deleted the SLA",
            )
        except Exception as e:
            print(e)
            return cr.error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Error while deleting the SLA",
            )

    def calculate_sla_response_time_percentage(
        self, response_time: int, created_at: datetime
    ) -> int:
        percentage = ((response_time - created_at.timestamp()) * 100) / response_time

        return int(percentage)

    def calculate_sla_resolution_time_percentage(
        self, resolution_time: int, created_at: datetime
    ) -> int:
        percentage = (
            resolution_time - (created_at.timestamp()) * 100
        ) / resolution_time

        return int(percentage)

    def check_ticket_sla_status(self, ticket: Ticket):
        response_time = self.calculate_sla_response_time_percentage(
            ticket.sla.response_time, ticket.created_at
        )
        resolution_time = self.calculate_sla_resolution_time_percentage(
            ticket.sla.resolution_time, ticket.created_at
        )

        return response_time, resolution_time


sla_service = SLAServices()
