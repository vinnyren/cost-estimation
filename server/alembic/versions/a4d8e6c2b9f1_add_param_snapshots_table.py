"""Add param_snapshots table

Revision ID: a4d8e6c2b9f1
Revises: 9b1c4f2e7a3d
Create Date: 2026-05-11 04:00:00.000000

v2.0 GAP-H — ParamManager 快照 tab 的存储基础。
ParamSnapshot 用于保存 effective_params 状态，scope 可以是 "global"
（全局 baseline）也可以是 project_id（项目 override 状态）。
"""
from alembic import op
import sqlalchemy as sa


revision = "a4d8e6c2b9f1"
down_revision = "9b1c4f2e7a3d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "param_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(), nullable=False, index=True),
        sa.Column("label", sa.String()),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_param_snapshots_scope", "param_snapshots", ["scope"]
    )


def downgrade():
    op.drop_index("ix_param_snapshots_scope", table_name="param_snapshots")
    op.drop_table("param_snapshots")
