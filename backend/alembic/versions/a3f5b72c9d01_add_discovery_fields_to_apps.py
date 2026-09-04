"""Add discovery fields to apps table — Phase 5

Revision ID: a3f5b72c9d01
Revises: 4ee61638ff5f
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f5b72c9d01"
down_revision: str | None = "4ee61638ff5f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "apps",
        sa.Column(
            "discovery_status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "apps",
        sa.Column("target_profile", sa.JSON(), nullable=True),
    )
    op.add_column(
        "apps",
        sa.Column("discovered_endpoints", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("apps", "discovered_endpoints")
    op.drop_column("apps", "target_profile")
    op.drop_column("apps", "discovery_status")
