"""Add api_keys, audit_jobs, audit_job_items tables for scan dashboard.

Revision ID: 002
Revises: 001
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("canvas_url", sa.String(), nullable=False),
        sa.Column("encrypted_token", sa.LargeBinary(), nullable=False),
        sa.Column("token_hint", sa.String(4), nullable=False),
        sa.Column("course_count", sa.Integer(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_api_keys_user_id", "api_keys", ["user_id"])

    op.create_table(
        "audit_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "api_key_id",
            sa.String(),
            sa.ForeignKey("api_keys.id"),
            nullable=False,
        ),
        sa.Column("canvas_url", sa.String(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("course_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_phase", sa.String(), nullable=True),
        sa.Column("current_item", sa.String(), nullable=True),
        sa.Column("items_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issues_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("checkpoint_json", sa.Text(), nullable=True),
        sa.Column("queue_position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("idx_audit_jobs_user_id", "audit_jobs", ["user_id"])
    op.create_index("idx_audit_jobs_status", "audit_jobs", ["status"])

    op.create_table(
        "audit_job_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(),
            sa.ForeignKey("audit_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("item_title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checked_at", sa.DateTime(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )
    op.create_index("idx_audit_job_items_job_id", "audit_job_items", ["job_id"])


def downgrade() -> None:
    op.drop_table("audit_job_items")
    op.drop_table("audit_jobs")
    op.drop_table("api_keys")
