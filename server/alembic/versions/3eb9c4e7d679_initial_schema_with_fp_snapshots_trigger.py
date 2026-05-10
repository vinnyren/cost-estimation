"""initial schema with fp_snapshots trigger
Revision ID: 3eb9c4e7d679
Revises:
Create Date: 2026-05-10 12:39:08.624911
"""
from alembic import op
import sqlalchemy as sa
from app.db.session import Base
from app.db import models  # noqa: F401  触发所有模型注册

revision = "3eb9c4e7d679"
down_revision = None
branch_labels = None
depends_on = None

TRIGGER_SQL = """
CREATE TRIGGER trim_fp_snapshots AFTER INSERT ON fp_snapshots
BEGIN
  DELETE FROM fp_snapshots
  WHERE project_id = NEW.project_id
    AND id NOT IN (
      SELECT id FROM fp_snapshots
      WHERE project_id = NEW.project_id
      ORDER BY id DESC LIMIT 5
    );
END;
"""


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    op.execute(TRIGGER_SQL)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trim_fp_snapshots")
    Base.metadata.drop_all(bind=op.get_bind())
