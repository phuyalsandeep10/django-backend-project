"""customer

Revision ID: 20250801_085704
Revises: 20250801_085215
Create Date: 2025-08-01 14:42:05.815483

"""

from typing import Sequence, Union

from migrations.base import BaseMigration

revision: str = "20250801_085704"
down_revision: Union[str, Sequence[str], None] = "20250801_085215"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class CustomerMigration(BaseMigration):

    table_name = "org_customers"

    def __init__(self):
        super().__init__(revision="20250801_085704", down_revision="20250801_085215")
        # describe your schemas here
        self.common_columns()
        self.foreign("organization_id", "sys_organizations")
        self.string("name", nullable=True)
        self.string("email", nullable=True)
        self.string("phone", nullable=True)
        self.string("address", nullable=True)
        self.string("ip_address", nullable=False)


def upgrade() -> None:
    """
    Function to create a table
    """
    CustomerMigration().upgrade()


def downgrade() -> None:
    """
    Function to drop a table
    """
    CustomerMigration().downgrade()
