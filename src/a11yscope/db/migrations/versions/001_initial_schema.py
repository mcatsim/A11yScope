"""Initial schema — users, app_settings, audit_log, refresh_tokens.

Revision ID: 001
Create Date: 2026-03-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), unique=True, nullable=False),
        sa.Column("display_name", sa.String(), nullable=False, server_default=""),
        sa.Column("role", sa.String(), nullable=False, server_default="auditor"),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("canvas_api_token_encrypted", sa.Text(), nullable=True),
        sa.Column("idp_subject", sa.String(), nullable=True),
        sa.Column("idp_provider", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("user_email", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="success"),
    )
    op.create_index("idx_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("idx_audit_log_user", "audit_log", ["user_id"])
    op.create_index("idx_audit_log_action", "audit_log", ["action"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("audit_log")
    op.drop_table("app_settings")
    op.drop_table("users")
