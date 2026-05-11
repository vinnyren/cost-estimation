"""Add audit_log table

Revision ID: b7e2f1d9c4a8
Revises: a4d8e6c2b9f1
Create Date: 2026-05-11 05:00:00.000000

v2.0 GAP-J — 项目级审计日志的存储基础。
audit_log 由 app/middleware/audit.py 在写操作（PATCH/POST/PUT/DELETE）
命中 /api/projects/* 时自动写入。actor 字段为 v3 多用户预留。
FK ondelete=CASCADE 与 ORM cascade="all, delete-orphan" 双重保证：
项目删除时审计日志一并清理。
"""
from alembic import op
import sqlalchemy as sa


revision = "b7e2f1d9c4a8"
down_revision = "a4d8e6c2b9f1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.String(),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("ts", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("actor", sa.String(), server_default="user"),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target", sa.String()),
        sa.Column("diff_json", sa.Text()),
    )
    op.create_index("ix_audit_log_project", "audit_log", ["project_id"])
    op.create_index("ix_audit_log_ts", "audit_log", ["ts"])
    op.create_index("ix_audit_log_project_ts", "audit_log", ["project_id", "ts"])


def downgrade():
    op.drop_index("ix_audit_log_project_ts", table_name="audit_log")
    op.drop_index("ix_audit_log_ts", table_name="audit_log")
    op.drop_index("ix_audit_log_project", table_name="audit_log")
    op.drop_table("audit_log")
