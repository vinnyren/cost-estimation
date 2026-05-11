"""v2.2 — services.calc.run_forward dict 包含 trace 和 composition。"""
import pytest
from app.services.calc import run_forward
from app.db.models import Project, FunctionPoint


def _seed_csbmk(db):
    """Seed CSBMK params so get_effective can resolve params."""
    from app.services import params as ps
    ps.seed_from_csbmk(db=db)
    db.commit()


def _seed_project(db, pid: str = "p-trace-test"):
    """Inline minimal Project + 1 FP for trace 测试."""
    p = Project(
        id=pid, name="trace 测试项目",
        project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务",
        mode="forward", basis_data_ver="CSBMK-202510",
    )
    db.add(p)
    db.commit()
    fp = FunctionPoint(
        id=f"fp-trace-{pid}", project_id=pid, name="X", category="EI",
        complexity="low", ufp=4, us=275.0,
    )
    db.add(fp)
    db.commit()
    return p


def test_run_forward_dict_has_trace(db_session):
    _seed_csbmk(db_session)
    _seed_project(db_session)
    payload = {
        "project_id": "p-trace-test",
        "dev_factor": 1.0, "ops_factor": 1.0,
        "include_dev": True, "include_ops": False,
        "other_cost": 25000.0,
    }
    res = run_forward(db_session, "p-trace-test", payload)
    assert "trace" in res
    assert "composition" in res
    assert res["trace"]["us"] == 275.0
    assert res["trace"]["s_adjusted"] > 0
    assert res["composition"]["dev_labor"] > 0
    assert res["composition"]["other"] == 25000.0


def test_run_forward_composition_sums_to_total(db_session):
    _seed_csbmk(db_session)
    _seed_project(db_session, "p-trace-test-2")
    payload = {
        "project_id": "p-trace-test-2",
        "dev_factor": 1.0, "ops_factor": 1.0,
        "include_dev": True, "include_ops": True,
        "other_cost": 10000.0,
    }
    res = run_forward(db_session, "p-trace-test-2", payload)
    c = res["composition"]
    total_sum = c["dev_labor"] + c["ops_labor"] + c["other"] + c["indirect"]
    assert abs(total_sum - res["cost_total_yuan"]["P50"]) < 1.0
