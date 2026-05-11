"""v2.2 — AiTask service smoke."""
import pytest
from app.services import ai_tasks as svc
from app.db.models import Project


def _seed_project(db, pid="p-ai-test"):
    p = Project(
        id=pid, name="ai task test",
        project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务",
        mode="forward", basis_data_ver="CSBMK-202510",
    )
    db.add(p)
    db.commit()
    return p


def test_create_and_progress(db_session):
    p = _seed_project(db_session)
    t = svc.create_task(db_session, p.id, "extract")
    assert t.status == "queued"
    assert t.progress_pct == 0.0
    assert t.id  # uuid populated

    t2 = svc.update_task(
        db_session, t.id,
        status="running", progress_pct=48.0,
        stage_log_append="✓ 章节切分",
    )
    assert t2 is not None
    assert t2.status == "running"
    assert t2.progress_pct == 48.0
    assert "章节切分" in t2.stage_log


def test_list_returns_recent_for_project(db_session):
    p = _seed_project(db_session, pid="p-ai-test-2")
    svc.create_task(db_session, p.id, "extract")
    svc.create_task(db_session, p.id, "allocate")
    listed = svc.list_for_project(db_session, p.id)
    assert len(listed) == 2
    # 最新在前
    assert listed[0].kind in ("extract", "allocate")


def test_update_returns_none_for_unknown_id(db_session):
    assert svc.update_task(db_session, "non-existent-id", status="done") is None
