"""measurement_method_and_cosmic

Revision ID: 6fd4cb76f438
Revises: f3a7d9e2c841
Create Date: 2026-05-19 12:00:00.000000

v2.9 — 多标准功能规模测量（measurement_method）+ COSMIC 数据移动列：
- projects.measurement_method 取代死字段 fp_method（值迁移后删除旧列）。
- function_points 新增 cosmic_entry / cosmic_exit / cosmic_read / cosmic_write。

dev 库兼容：本项目 bootstrap 用 create_all，dev 库可能无 alembic 版本戳，
无法 `alembic upgrade head`。此时手动执行：
  ALTER TABLE projects ADD COLUMN measurement_method VARCHAR NOT NULL DEFAULT 'nesma_estimated';
  ALTER TABLE projects DROP COLUMN fp_method;
  ALTER TABLE function_points ADD COLUMN cosmic_entry INTEGER;
  ALTER TABLE function_points ADD COLUMN cosmic_exit INTEGER;
  ALTER TABLE function_points ADD COLUMN cosmic_read INTEGER;
  ALTER TABLE function_points ADD COLUMN cosmic_write INTEGER;
"""
from alembic import op
import sqlalchemy as sa

revision = "6fd4cb76f438"
down_revision = "f3a7d9e2c841"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column(
            "measurement_method", sa.String(),
            server_default="nesma_estimated", nullable=False,
        ))
    op.execute(
        "UPDATE projects SET measurement_method = fp_method "
        "WHERE fp_method IN ('ifpug', 'nesma_estimated')"
    )
    op.execute(
        "UPDATE projects SET measurement_method = 'nesma_estimated' "
        "WHERE fp_method = 'quick'"
    )
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("fp_method")
    with op.batch_alter_table("function_points") as batch:
        batch.add_column(sa.Column("cosmic_entry", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("cosmic_exit",  sa.Integer(), nullable=True))
        batch.add_column(sa.Column("cosmic_read",  sa.Integer(), nullable=True))
        batch.add_column(sa.Column("cosmic_write", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("function_points") as batch:
        batch.drop_column("cosmic_write")
        batch.drop_column("cosmic_read")
        batch.drop_column("cosmic_exit")
        batch.drop_column("cosmic_entry")
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column(
            "fp_method", sa.String(),
            server_default="nesma_estimated", nullable=True,
        ))
    op.execute("UPDATE projects SET fp_method = measurement_method")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("measurement_method")
