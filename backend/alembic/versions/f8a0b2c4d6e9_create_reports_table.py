"""Create reports table - Phase 13 (Reporting Engine)

Revision ID: f8a0b2c4d6e9
Revises: f8a0b2c4d6e8
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a0b2c4d6e9"
down_revision: str | None = "f8a0b2c4d6e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
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
            sa.ForeignKey("test_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "app_id",
            UUID(as_uuid=True),
            sa.ForeignKey("apps.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("pdf_path", sa.String(length=512), nullable=True),
        sa.Column("csv_path", sa.String(length=512), nullable=True),
        sa.Column("before_after_comparison", JSON, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metrics_summary", JSON, nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_reports_org_id", "reports", ["org_id"])
    op.create_index("ix_reports_test_run_id", "reports", ["test_run_id"])
    op.create_index("ix_reports_app_id", "reports", ["app_id"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_index("ix_reports_app_id", table_name="reports")
    op.drop_index("ix_reports_test_run_id", table_name="reports")
    op.drop_index("ix_reports_org_id", table_name="reports")
    op.drop_table("reports")
