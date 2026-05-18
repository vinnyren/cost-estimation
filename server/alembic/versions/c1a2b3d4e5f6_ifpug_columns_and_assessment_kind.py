"""ifpug_columns_and_assessment_kind

Revision ID: c1a2b3d4e5f6
Revises: 4b7939b0712d
Create Date: 2026-05-18 09:00:00.000000

v2.8 Part A：
- function_points 新增 det/ret/ftr（IFPUG GB/T 42449 复杂度查表输入），均可空。
- function_points.modify_type 旧值 'new' 迁移为 'add'（对齐 42449 ADD/CHGA/DEL/CFP）。
- projects 新增 assessment_kind（development | enhancement），默认 development。

dev 库兼容：本项目 bootstrap 用 create_all，dev 库可能无 alembic 版本戳，
无法 `alembic upgrade head`。此时手动执行：
  ALTER TABLE function_points ADD COLUMN det INTEGER;
  ALTER TABLE function_points ADD COLUMN ret INTEGER;
  ALTER TABLE function_points ADD COLUMN ftr INTEGER;
  ALTER TABLE projects ADD COLUMN assessment_kind VARCHAR DEFAULT 'development' NOT NULL;
  UPDATE function_points SET modify_type='add' WHERE modify_type='new';
  UPDATE function_points SET modify_type='change' WHERE modify_type='modify';
"""
from alembic import op
import sqlalchemy as sa


revision = "c1a2b3d4e5f6"
down_revision = "4b7939b0712d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("function_points") as batch:
        batch.add_column(sa.Column("det", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("ret", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("ftr", sa.Integer(), nullable=True))
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column(
            "assessment_kind", sa.String(),
            server_default="development", nullable=False,
        ))
    op.execute(
        "UPDATE function_points SET modify_type='add' WHERE modify_type='new'"
    )
    op.execute(
        "UPDATE function_points SET modify_type='change' WHERE modify_type='modify'"
    )


def downgrade():
    op.execute(
        "UPDATE function_points SET modify_type='new' WHERE modify_type='add'"
    )
    op.execute(
        "UPDATE function_points SET modify_type='modify' WHERE modify_type='change'"
    )
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("assessment_kind")
    with op.batch_alter_table("function_points") as batch:
        batch.drop_column("ftr")
        batch.drop_column("ret")
        batch.drop_column("det")
