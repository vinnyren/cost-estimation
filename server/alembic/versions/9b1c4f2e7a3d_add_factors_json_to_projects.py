"""Add factors_dev_json + factors_ops_json to projects

Revision ID: 9b1c4f2e7a3d
Revises: 8a2e6b41c3d7
Create Date: 2026-05-11 03:10:00.000000

v1.1 calc.py 用 payload.get("dev_factor", 1.0)，永远是 1.0。
v2.0 改为读 Project.factors_dev_json，本 migration 给老项目预留 NULL，
calc.py 在读到 NULL 时 fallback 1.0 + 给 Result.warning_messages 加提示。
"""
from alembic import op
import sqlalchemy as sa


revision = "9b1c4f2e7a3d"
down_revision = "8a2e6b41c3d7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("factors_dev_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("factors_ops_json", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("factors_ops_json")
        batch.drop_column("factors_dev_json")
