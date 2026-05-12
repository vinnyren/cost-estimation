"""add_pid_to_ai_tasks
Revision ID: e5be802ba4f1
Revises: fc7d856b9030
Create Date: 2026-05-12 12:26:41.137792
"""
from alembic import op
import sqlalchemy as sa


revision = 'e5be802ba4f1'
down_revision = 'fc7d856b9030'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('ai_tasks', sa.Column('pid', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('ai_tasks', 'pid')
