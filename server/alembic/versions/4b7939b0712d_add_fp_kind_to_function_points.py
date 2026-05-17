"""add_fp_kind_to_function_points
Revision ID: 4b7939b0712d
Revises: e5be802ba4f1
Create Date: 2026-05-17 16:50:53.232315
"""
from alembic import op
import sqlalchemy as sa


revision = '4b7939b0712d'
down_revision = 'e5be802ba4f1'
branch_labels = None
depends_on = None


def upgrade():
    # autogenerate 还捕获了一批无关的 FK rename noise（既有 ondelete=CASCADE
    # FK 被反复 drop/recreate）—— 那些是 SQLite 反射误判，与本次变更无关，已删除。
    # 本 migration 只新增 function_points.fp_kind 列。
    op.add_column(
        'function_points',
        sa.Column('fp_kind', sa.String(), server_default='dev', nullable=False),
    )


def downgrade():
    op.drop_column('function_points', 'fp_kind')
