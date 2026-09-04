"""Create routes table - Phase 8

Revision ID: c5d7e9f1a3b4
Revises: b4c6d8e0f1a2
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "c5d7e9f1a3b4"
down_revision: str | None = "b4c6d8e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "routes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("test_run_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "app_id",
            UUID(as_uuid=True),
            sa.ForeignKey("apps.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("target_service", sa.String(255), nullable=False),
        sa.Column("target_port", sa.Integer(), nullable=False),
        sa.Column("path_prefix", sa.String(255), nullable=False, server_default="/"),
        sa.Column("route_url", sa.String(512), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default="1800"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(255), nullable=True),
        sa.Column("ingress_name", sa.String(255), nullable=True),
        sa.Column("namespace", sa.String(255), nullable=False),
    )
    op.create_index("ix_routes_org_id", "routes", ["org_id"])
    op.create_index("ix_routes_test_run_id", "routes", ["test_run_id"])
    op.create_index("ix_routes_app_id", "routes", ["app_id"])
    op.create_index("ix_routes_status", "routes", ["status"])
    op.create_index("ix_routes_expires_at", "routes", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_routes_expires_at", table_name="routes")
    op.drop_index("ix_routes_status", table_name="routes")
    op.drop_index("ix_routes_app_id", table_name="routes")
    op.drop_index("ix_routes_test_run_id", table_name="routes")
    op.drop_index("ix_routes_org_id", table_name="routes")
    op.drop_table("routes")
