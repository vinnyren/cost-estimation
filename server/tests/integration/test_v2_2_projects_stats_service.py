"""v2.2 — projects.get_stats 单测：counts + monthly_count（adapted: 无 status 列）."""
import pytest
from datetime import datetime, timezone
from app.services import projects as ps
from app.db.models import Project, FunctionPoint


def test_get_stats_counts_total_and_monthly(db_session):
    now = datetime.now(timezone.utc)
    db_session.add_all([
        Project(id="s-1", name="P1", project_type="dev_only", phase="bidding",
                city="北京", industry="电子政务", mode="forward",
                basis_data_ver="CSBMK-202510"),
        Project(id="s-2", name="P2", project_type="dev_only", phase="bidding",
                city="北京", industry="电子政务", mode="forward",
                basis_data_ver="CSBMK-202510"),
    ])
    db_session.commit()
    stats = ps.get_stats(db_session, month=now.strftime("%Y-%m"))
    assert stats["counts"]["total"] == 2
    assert stats["counts"]["draft"] == 2  # 都没 function_points
    assert stats["counts"]["in_progress"] == 0
    assert stats["counts"]["archived"] == 0
    assert stats["counts"]["delivered"] == 0
    assert stats["monthly_count"] == 2  # 都本月创建
    assert stats["monthly_p50_sum"] == 0.0
    assert stats["monthly_growth_pct"] == 0.0


def test_get_stats_in_progress_when_has_fps(db_session):
    """有 FP 但还未计算 → in_progress count."""
    now = datetime.now(timezone.utc)
    p = Project(id="s-3", name="P3", project_type="dev_only", phase="bidding",
                city="北京", industry="电子政务", mode="forward",
                basis_data_ver="CSBMK-202510")
    db_session.add(p)
    db_session.commit()
    fp = FunctionPoint(
        id="fp-1", project_id="s-3", name="X",
        category="EI", complexity="average", ufp=4.0, us=4.0,
    )
    db_session.add(fp)
    db_session.commit()
    stats = ps.get_stats(db_session, month=now.strftime("%Y-%m"))
    assert stats["counts"]["in_progress"] == 1
    assert stats["counts"]["draft"] == 0  # P3 has FP, so not draft
