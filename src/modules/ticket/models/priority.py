from typing import TYPE_CHECKING, ClassVar, List

from sqlmodel import Relationship, UniqueConstraint, func

import src.modules.ticket.services.mixins as Mixin
from src.common.models import TenantModel
from src.modules.ticket.enums import TicketLogEntityEnum

if TYPE_CHECKING:
    from src.modules.organizations.models import Organization
    from src.modules.ticket.models.sla import TicketSLA
    from src.modules.ticket.models.ticket import Ticket


class TicketPriority(TenantModel, Mixin.LoggingMixin, table=True):
    """
    Ticket Priority model
    """

    __tablename__ = "ticket_priority"  # type:ignore
    entity_type: ClassVar[TicketLogEntityEnum] = TicketLogEntityEnum.TICKET_PRIORITY
    name: str
    level: int
    bg_color: str
    fg_color: str
    tickets: List["Ticket"] = Relationship(back_populates="priority")
    sla: "TicketSLA" = Relationship(back_populates="priority")
    organization: "Organization" = Relationship(back_populates="ticket_priorities")

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "name",
            "level",
            name="uniq_org_ticket_priority_name_level",
        ),
        UniqueConstraint(
            "organization_id",
            "level",
            name="uniq_org_ticket_priority_level",
        ),
        UniqueConstraint(
            "organization_id",
            "name",
            name="uniq_org_ticket_priority_name",
        ),
    )

    def __str__(self):
        return f"{self.name}-{self.organization_id}"
