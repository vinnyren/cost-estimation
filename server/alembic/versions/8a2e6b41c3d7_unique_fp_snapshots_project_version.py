"""UNIQUE(project_id, version) on fp_snapshots

Revision ID: 8a2e6b41c3d7
Revises: 3eb9c4e7d679
Create Date: 2026-05-11 02:55:00.000000

Discovered by /review round 5 adversarial pass: without UNIQUE, two parallel
bulk_write calls can both read max(version)=N, both write rows at version=N+1,
and both write FPSnapshot rows at version=N+1. restore(version=N+1) then
becomes non-deterministic. Adding the constraint forces one writer to fail
fast with IntegrityError instead of silently corrupting state.

Migration also dedups any pre-existing duplicates (keep highest id per group)
so production DBs with race-induced duplicates don't block the upgrade.
"""
from alembic import op


revision = "8a2e6b41c3d7"
down_revision = "3eb9c4e7d679"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Dedup: keep the latest id per (project_id, version)
    op.execute(
        """
        DELETE FROM fp_snapshots
        WHERE id NOT IN (
            SELECT MAX(id) FROM fp_snapshots
            GROUP BY project_id, version
        )
        """
    )
    # 2) Add the constraint. SQLite does not support ADD CONSTRAINT directly;
    # use a unique index instead (logically equivalent for INSERT guards).
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "uq_fp_snapshots_project_version "
        "ON fp_snapshots (project_id, version)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_fp_snapshots_project_version")
