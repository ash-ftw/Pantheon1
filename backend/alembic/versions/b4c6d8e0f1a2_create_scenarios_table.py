"""Create scenarios table - Phase 6

Revision ID: b4c6d8e0f1a2
Revises: a3f5b72c9d01
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c6d8e0f1a2"
down_revision: str | None = "a3f5b72c9d01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="custom"),
        sa.Column("is_preset", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_scenarios_org_id", "scenarios", ["org_id"])
    op.create_index("ix_scenarios_category", "scenarios", ["category"])
    op.create_index("ix_scenarios_slug", "scenarios", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_scenarios_slug", table_name="scenarios")
    op.drop_index("ix_scenarios_category", table_name="scenarios")
    op.drop_index("ix_scenarios_org_id", table_name="scenarios")
    op.drop_table("scenarios")
