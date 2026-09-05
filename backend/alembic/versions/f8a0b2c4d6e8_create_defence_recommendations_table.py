"""Create defence_recommendations table - Phase 11

Revision ID: f8a0b2c4d6e8
Revises: e7f9a1b3c5d7
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a0b2c4d6e8"
down_revision: str | None = "e7f9a1b3c5d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "defence_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "test_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("test_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "app_id",
            UUID(as_uuid=True),
            sa.ForeignKey("apps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column(
            "mitigation_type",
            sa.String(length=50),
            nullable=False,
            server_default="infrastructure",
        ),
        sa.Column(
            "mechanically_applicable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="suggested",
        ),
        sa.Column("code_guidance", sa.Text(), nullable=False),
        sa.Column("infra_manifest", JSON, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("target_resource", sa.String(length=255), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_defence_recommendations_org_id",
        "defence_recommendations",
        ["org_id"],
    )
    op.create_index(
        "ix_defence_recommendations_test_run_id",
        "defence_recommendations",
        ["test_run_id"],
    )
    op.create_index(
        "ix_defence_recommendations_finding_id",
        "defence_recommendations",
        ["finding_id"],
    )
    op.create_index(
        "ix_defence_recommendations_app_id",
        "defence_recommendations",
        ["app_id"],
    )
    op.create_index(
        "ix_defence_recommendations_category",
        "defence_recommendations",
        ["category"],
    )
    op.create_index(
        "ix_defence_recommendations_status",
        "defence_recommendations",
        ["status"],
    )
    op.create_index(
        "ix_defence_recommendations_created_at",
        "defence_recommendations",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("defence_recommendations")
