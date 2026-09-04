"""Create test_runs and findings tables - Phase 9

Revision ID: d6e8f0a2b4c6
Revises: c5d7e9f1a3b4
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

# revision identifiers, used by Alembic.
revision: str = "d6e8f0a2b4c6"
down_revision: str | None = "c5d7e9f1a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create test_runs table
    op.create_table(
        "test_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "org_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orgs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "app_id",
            UUID(as_uuid=True),
            sa.ForeignKey("apps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scenario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scenarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("scenario_name", sa.String(255), nullable=False),
        sa.Column("scenario_category", sa.String(50), nullable=False),
        sa.Column(
            "route_id",
            UUID(as_uuid=True),
            sa.ForeignKey("routes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_steps", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_step_name", sa.String(255), nullable=True),
        sa.Column("parameters", JSON, nullable=False, server_default="{}"),
        sa.Column("metrics", JSON, nullable=False, server_default="{}"),
        sa.Column("logs", JSON, nullable=False, server_default="[]"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_test_runs_org_id", "test_runs", ["org_id"])
    op.create_index("ix_test_runs_app_id", "test_runs", ["app_id"])
    op.create_index("ix_test_runs_scenario_id", "test_runs", ["scenario_id"])
    op.create_index("ix_test_runs_route_id", "test_runs", ["route_id"])
    op.create_index("ix_test_runs_status", "test_runs", ["status"])
    op.create_index("ix_test_runs_created_at", "test_runs", ["created_at"])

    # 2. Create findings table
    op.create_table(
        "findings",
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
            "app_id",
            UUID(as_uuid=True),
            sa.ForeignKey("apps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("cwe_id", sa.String(50), nullable=True),
        sa.Column("owasp_category", sa.String(100), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("evidence", JSON, nullable=False, server_default="{}"),
        sa.Column("remediation_guidance", sa.String(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_findings_org_id", "findings", ["org_id"])
    op.create_index("ix_findings_test_run_id", "findings", ["test_run_id"])
    op.create_index("ix_findings_app_id", "findings", ["app_id"])
    op.create_index("ix_findings_severity", "findings", ["severity"])
    op.create_index("ix_findings_category", "findings", ["category"])
    op.create_index("ix_findings_created_at", "findings", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_findings_created_at", table_name="findings")
    op.drop_index("ix_findings_category", table_name="findings")
    op.drop_index("ix_findings_severity", table_name="findings")
    op.drop_index("ix_findings_app_id", table_name="findings")
    op.drop_index("ix_findings_test_run_id", table_name="findings")
    op.drop_index("ix_findings_org_id", table_name="findings")
    op.drop_table("findings")

    op.drop_index("ix_test_runs_created_at", table_name="test_runs")
    op.drop_index("ix_test_runs_status", table_name="test_runs")
    op.drop_index("ix_test_runs_route_id", table_name="test_runs")
    op.drop_index("ix_test_runs_scenario_id", table_name="test_runs")
    op.drop_index("ix_test_runs_app_id", table_name="test_runs")
    op.drop_index("ix_test_runs_org_id", table_name="test_runs")
    op.drop_table("test_runs")
