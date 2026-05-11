"""add_ai_tasks_table
Revision ID: fc7d856b9030
Revises: b7e2f1d9c4a8
Create Date: 2026-05-11 18:52:41.658931
"""
from alembic import op
import sqlalchemy as sa


revision = 'fc7d856b9030'
down_revision = 'b7e2f1d9c4a8'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'ai_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('progress_pct', sa.Float(), nullable=False),
        sa.Column('stage_log', sa.Text(), nullable=False),
        sa.Column('output_json', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_tasks_project_id'), 'ai_tasks', ['project_id'], unique=False)
    op.create_index('ix_ai_tasks_project_status', 'ai_tasks', ['project_id', 'status'], unique=False)


def downgrade():
    op.drop_index('ix_ai_tasks_project_status', table_name='ai_tasks')
    op.drop_index(op.f('ix_ai_tasks_project_id'), table_name='ai_tasks')
    op.drop_table('ai_tasks')
