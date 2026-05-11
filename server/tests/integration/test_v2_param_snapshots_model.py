"""GAP-H foundation: ParamSnapshot 表 + 模型，给 ParamManager 快照 tab 用。"""
import json


def test_param_snapshot_can_be_inserted(db_session):
    from app.db.models import ParamSnapshot
    snap = ParamSnapshot(
        scope="global", label="实验前 baseline",
        payload_json=json.dumps({"hours_per_pm": 176}))
    db_session.add(snap)
    db_session.commit()
    db_session.refresh(snap)
    assert snap.id > 0
    assert snap.scope == "global"
    assert json.loads(snap.payload_json)["hours_per_pm"] == 176


def test_param_snapshot_scope_can_be_project_id(db_session):
    from app.db.models import ParamSnapshot
    snap = ParamSnapshot(scope="proj-abc-123", payload_json="{}")
    db_session.add(snap)
    db_session.commit()
    assert snap.scope == "proj-abc-123"
