"""Create attack_graph_nodes and attack_graph_edges tables - Phase 10

Revision ID: e7f9a1b3c5d7
Revises: d6e8f0a2b4c6
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f9a1b3c5d7"
down_revision: str | None = "d6e8f0a2b4c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create attack_graph_nodes table
    op.create_table(
        "attack_graph_nodes",
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
        sa.Column("node_id", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("node_type", sa.String(length=50), nullable=False, server_default="endpoint"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="probing"),
        sa.Column("step_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position_x", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("position_y", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", JSON, nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_attack_graph_nodes_org_id", "attack_graph_nodes", ["org_id"])
    op.create_index("ix_attack_graph_nodes_test_run_id", "attack_graph_nodes", ["test_run_id"])
    op.create_index("ix_attack_graph_nodes_created_at", "attack_graph_nodes", ["created_at"])

    # 2. Create attack_graph_edges table
    op.create_table(
        "attack_graph_edges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "test_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("test_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("edge_id", sa.String(length=100), nullable=False),
        sa.Column("source_node_id", sa.String(length=100), nullable=False),
        sa.Column("target_node_id", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="traversed"),
        sa.Column("step_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", JSON, nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_attack_graph_edges_test_run_id", "attack_graph_edges", ["test_run_id"])
    op.create_index("ix_attack_graph_edges_created_at", "attack_graph_edges", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_attack_graph_edges_created_at", table_name="attack_graph_edges")
    op.drop_index("ix_attack_graph_edges_test_run_id", table_name="attack_graph_edges")
    op.drop_table("attack_graph_edges")

    op.drop_index("ix_attack_graph_nodes_created_at", table_name="attack_graph_nodes")
    op.drop_index("ix_attack_graph_nodes_test_run_id", table_name="attack_graph_nodes")
    op.drop_index("ix_attack_graph_nodes_org_id", table_name="attack_graph_nodes")
    op.drop_table("attack_graph_nodes")
