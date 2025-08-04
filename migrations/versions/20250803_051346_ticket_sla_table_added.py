"""ticket sla table added

Revision ID: 20250803_051346
Revises: 20250803_050421
Create Date: 2025-08-03 10:58:47.312924

"""

from typing import Sequence, Union

from migrations.base import BaseMigration

revision: str = "20250803_051346"
down_revision: Union[str, Sequence[str], None] = "20250803_050421"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class TicketSLAMigration(BaseMigration):

    table_name = "ticket_sla"

    def __init__(self):
        super().__init__(revision="20250803_051346", down_revision="20250803_050421")
        self.create_whole_table = True
        # describe your schemas here
        self.tenant_columns()
        self.string(name="name")
        self.biginteger(name="response_time")
        self.biginteger(name="resolution_time")
        self.boolean(name="is_default")


def upgrade() -> None:
    """
    Function to create a table
    """
    TicketSLAMigration().upgrade()


def downgrade() -> None:
    """
    Function to drop a table
    """
    TicketSLAMigration().downgrade()
