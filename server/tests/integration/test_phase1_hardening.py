"""Phase 1 hardening: docs disabled in prod / override marks Result stale /
allocate rejects unknown project_id.

These cover ISSUE-008/011/012 from rounds 1+2 QA — all originally deferred
because they were defense-in-depth or design-debt rather than user-facing
bugs, batched here once we decided to close out the QA backlog.
"""
import json
import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    db_file = f"/tmp/cost-test-{uuid.uuid4()}.sqlite"
    monkeypatch.setenv("COST_DB_PATH", db_file)
    monkeypatch.delenv("COST_WEB_DIST_DIR", raising=False)
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.projects", "app.services.calc",
              "app.services.functions",
              "app.api.projects", "app.api.params", "app.api.calc",
              "app.api.functions", "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def prod_client(monkeypatch, tmp_path):
    """模拟生产期：挂 web/dist 时应当关掉 /docs /openapi.json。"""
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    db_file = f"/tmp/cost-test-{uuid.uuid4()}.sqlite"
    monkeypatch.setenv("COST_DB_PATH", db_file)
    # 制造一个最小的 dist 目录，只为触发 docs_url=None 分支
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    monkeypatch.setenv("COST_WEB_DIST_DIR", str(dist))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.projects", "app.services.calc",
              "app.services.functions",
              "app.api.projects", "app.api.params", "app.api.calc",
              "app.api.functions", "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ----- ISSUE-008: docs / openapi disabled in production -----

async def test_docs_available_in_dev_mode(client):
    """开发模式（无 web_dist_dir）保留 /docs 用于联调。"""
    r = await client.get("/docs")
    assert r.status_code == 200


async def test_docs_disabled_when_web_dist_mounted(prod_client):
    """生产期 FastAPI 不再注册 /docs；SPA fallback 会把 path 兜底成
    index.html，所以 status 是 200 但内容不是 Swagger UI（关键是 schema
    不再以 JSON 形式被外部抓取到）。"""
    r = await prod_client.get("/docs")
    if r.status_code == 200:
        assert "swagger-ui" not in r.text.lower()
        assert "<html" in r.text.lower()
    else:
        assert r.status_code == 404


async def test_openapi_disabled_when_web_dist_mounted(prod_client):
    # /openapi.json 也走 GET 非-/api，会被 SPA fallback 接管 → 返回 index.html
    # 关键是 FastAPI 不再 *主动暴露* JSON schema。SPA 兜底返回 200 但不是 schema。
    r = await prod_client.get("/openapi.json")
    body_text = r.text[:200]
    # 不是 JSON schema 的特征（没有 "openapi" 顶层 key）
    if r.status_code == 200:
        try:
            data = r.json()
            assert "openapi" not in data and "paths" not in data
        except (json.JSONDecodeError, ValueError):
            # SPA shell — 期望
            pass
    else:
        assert r.status_code == 404


# ----- ISSUE-011: override 后 Result 行被标记 stale -----

async def test_override_marks_existing_result_stale(client):
    rp = await client.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    pid = rp.json()["data"]["id"]

    # 直接在 DB 里插一条假的 Result 行（calc 当前不写 Result，但缓存表
    # 已建好；本测试覆盖「未来打开缓存后 override 会正确 invalidate」）
    from app.db.session import SessionLocal
    from app.db.models import Result
    db = SessionLocal()
    try:
        db.add(Result(project_id=pid, mode="forward", fp_version=1,
                      params_hash="abc", payload_json="{}", is_stale=False))
        db.commit()

        r = await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"city_rate.北京.dev": 50000},
        )
        assert r.status_code == 200
        # 重新查
        rows = db.query(Result).filter_by(project_id=pid).all()
        assert all(row.is_stale for row in rows)
    finally:
        db.close()


# ----- ISSUE-012: allocate 拒绝不存在的 project_id -----

async def test_allocate_unknown_project_404(client):
    r = await client.post(
        "/api/calc/allocate",
        headers={**H, "Content-Type": "application/json"},
        json={
            "project_id": "prj-does-not-exist",
            "target_us": 100,
            "cf": 1.21,
            "drafts": [{"name": "A", "weight": 1}],
        },
    )
    assert r.status_code == 404


async def test_allocate_existing_project_still_works(client):
    rp = await client.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    pid = rp.json()["data"]["id"]
    r = await client.post(
        "/api/calc/allocate",
        headers={**H, "Content-Type": "application/json"},
        json={
            "project_id": pid,
            "target_us": 100,
            "cf": 1.21,
            "drafts": [{"name": "A", "weight": 1}, {"name": "B", "weight": 2}],
        },
    )
    assert r.status_code == 200
    assert len(r.json()["data"]) == 2
