"""project_selected_band

Revision ID: f3a7d9e2c841
Revises: c1a2b3d4e5f6
Create Date: 2026-05-19 09:00:00.000000

v2.9 — 用户在结果页选定的成本档位持久化：
- projects 新增 selected_band（P10 / P50 / P90），默认 P50。
  决定报告导出时选用哪一档作为「评估结论」主值。

dev 库兼容：本项目 bootstrap 用 create_all，dev 库可能无 alembic 版本戳，
无法 `alembic upgrade head`。此时手动执行：
  ALTER TABLE projects ADD COLUMN selected_band VARCHAR DEFAULT 'P50' NOT NULL;
"""
from alembic import op
import sqlalchemy as sa


revision = "f3a7d9e2c841"
down_revision = "c1a2b3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column(
            "selected_band", sa.String(),
            server_default="P50", nullable=False,
        ))


def downgrade():
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("selected_band")
