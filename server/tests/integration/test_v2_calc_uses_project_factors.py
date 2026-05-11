"""GAP-B 闭环：calc 用 project.factors_*_json 替代默认 1.0。

Task T7：service.calc.run_forward / run_reverse 真正读项目 factors_dev_json /
factors_ops_json，按 effective_params["factors_dev"] / ["factors_ops"]
查表得到乘子链，缺失时回退 1.0 并附 warning_messages。
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in [
        "app.config",
        "app.db.session",
        "app.deps",
        "app.db.models",
        "app.services.params",
        "app.services.factors",
        "app.services.calc",
        "app.services.projects",
        "app.api.projects",
        "app.api.params",
        "app.api.functions",
        "app.api.calc",
        "app.api.health",
        "app.main",
    ]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed(c, factors_dev=None, factors_ops=None, include_ops=False):
    r = await c.post(
        "/api/projects",
        headers=H,
        json={
            "name": "T",
            "project_type": "dev_and_ops" if include_ops else "dev_only",
            "phase": "bidding",
            "city": "北京",
            "industry": "电子政务",
            "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
            "include_ops": include_ops,
            "factors_dev": factors_dev,
            "factors_ops": factors_ops,
        },
    )
    assert r.status_code in (200, 201), r.text
    pid = r.json()["data"]["id"]
    fp = await c.post(
        f"/api/projects/{pid}/functions",
        headers=H,
        json={
            "name": "fp1",
            "category": "EI",
            "complexity": "low",
            "ufp": 3,
            "us": 3,
            "source": "manual",
        },
    )
    assert fp.status_code in (200, 201), fp.text
    return pid


async def test_calc_with_factors_differs_from_default(client):
    """有 factors 选择的项目，其 cost 应当≠按 1.0 默认计算的结果。"""
    # 默认项目：factors_dev=None → fallback 1.0
    pid_default = await _seed(client, factors_dev=None)
    # 选了一组真实的 seed 表内键（v 非 1.0），乘子链一定 != 1.0
    # app_type=智能信息 (1.5), integrity_level=A/B (1.1), platform=C (1.5),
    # team_bg=none (1.2) → 1.5 × 1.1 × 1.5 × 1.2 × 1.0 = 2.97
    pid_with = await _seed(
        client,
        factors_dev={
            "app_type": "智能信息",
            "integrity_level": "A/B",
            "non_func": {
                "distributed": 0,
                "performance": 0,
                "reliability": 0,
                "multi_site": 0,
            },
            "platform": "C",
            "team_bg": "none",
        },
    )

    r1 = await client.post(
        "/api/calc/forward", headers=H, json={"project_id": pid_default}
    )
    assert r1.status_code == 200, r1.text
    r2 = await client.post(
        "/api/calc/forward", headers=H, json={"project_id": pid_with}
    )
    assert r2.status_code == 200, r2.text

    cost_default = r1.json()["data"]["cost_total_yuan"]["P50"]
    cost_with = r2.json()["data"]["cost_total_yuan"]["P50"]
    assert cost_default != cost_with, (
        "factors 应该真正影响 cost，不能 silently 用 1.0"
    )
    # sanity: 选了放大因子 → cost 应当更大
    assert cost_with > cost_default


async def test_calc_warning_when_factors_null(client):
    pid = await _seed(client, factors_dev=None)
    r = await client.post(
        "/api/calc/forward", headers=H, json={"project_id": pid}
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert "warning_messages" in body
    assert any("调整因子" in m for m in body["warning_messages"])


async def test_calc_no_warning_when_factors_present(client):
    pid = await _seed(
        client,
        factors_dev={
            "app_type": "业务处理",
            "integrity_level": "C/D",
            "non_func": {
                "distributed": 0,
                "performance": 0,
                "reliability": 0,
                "multi_site": 0,
            },
            "platform": "JAVA",
            "team_bg": "related",
        },
    )
    r = await client.post(
        "/api/calc/forward", headers=H, json={"project_id": pid}
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    msgs = body.get("warning_messages") or []
    assert all("调整因子" not in m for m in msgs)


async def test_calc_reverse_picks_up_factors(client):
    """Reverse 模式：dev_factor 必须从 project.factors_dev_json 派生。"""
    pid_default = await _seed(client, factors_dev=None)
    pid_with = await _seed(
        client,
        factors_dev={
            "app_type": "智能信息",
            "integrity_level": "A/B",
            "non_func": {
                "distributed": 0,
                "performance": 0,
                "reliability": 0,
                "multi_site": 0,
            },
            "platform": "C",
            "team_bg": "none",
        },
    )
    r1 = await client.post(
        "/api/calc/reverse",
        headers=H,
        json={"project_id": pid_default, "target_total": 1_000_000},
    )
    r2 = await client.post(
        "/api/calc/reverse",
        headers=H,
        json={"project_id": pid_with, "target_total": 1_000_000},
    )
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text
    # 不同的 dev_factor → 不同的反算 scale
    s1 = r1.json()["data"]["scale_adjusted_bands"]["P50"]
    s2 = r2.json()["data"]["scale_adjusted_bands"]["P50"]
    assert s1 != s2
