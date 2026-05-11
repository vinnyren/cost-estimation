"""Phase 1 hardening: docs disabled in prod / override marks Result stale /
allocate rejects unknown project_id.

These cover ISSUE-008/011/012 from rounds 1+2 QA — all originally deferred
because they were defense-in-depth or design-debt rather than user-facing
bugs, batched here once we decided to close out the QA backlog.
"""
import json

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


# ----- ISSUE-008: docs / openapi disabled in production -----

async def test_docs_available_in_dev_mode(client_factory, monkeypatch):
    """开发模式（无 web_dist_dir）保留 /docs 用于联调。"""
    monkeypatch.delenv("COST_WEB_DIST_DIR", raising=False)
    async with await client_factory() as client:
        r = await client.get("/docs")
        assert r.status_code == 200


async def test_docs_disabled_when_web_dist_mounted(client_factory, monkeypatch, tmp_path):
    """生产期 FastAPI 不再注册 /docs；SPA fallback 会把 path 兜底成
    index.html，所以 status 是 200 但内容不是 Swagger UI（关键是 schema
    不再以 JSON 形式被外部抓取到）。"""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    monkeypatch.setenv("COST_WEB_DIST_DIR", str(dist))
    async with await client_factory() as client:
        r = await client.get("/docs")
        if r.status_code == 200:
            assert "swagger-ui" not in r.text.lower()
            assert "<html" in r.text.lower()
        else:
            assert r.status_code == 404


async def test_openapi_disabled_when_web_dist_mounted(client_factory, monkeypatch, tmp_path):
    # /openapi.json 也走 GET 非-/api，会被 SPA fallback 接管 → 返回 index.html
    # 关键是 FastAPI 不再 *主动暴露* JSON schema。SPA 兜底返回 200 但不是 schema。
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    monkeypatch.setenv("COST_WEB_DIST_DIR", str(dist))
    async with await client_factory() as client:
        r = await client.get("/openapi.json")
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

async def test_override_marks_existing_result_stale(client_factory, db_session):
    async with await client_factory() as client:
        rp = await client.post("/api/projects", headers=H, json={
            "name": "T", "project_type": "dev_only", "phase": "bidding",
            "city": "北京", "industry": "电子政务", "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
        })
        pid = rp.json()["data"]["id"]

        # 直接在 DB 里插一条假的 Result 行（calc 当前不写 Result，但缓存表
        # 已建好；本测试覆盖「未来打开缓存后 override 会正确 invalidate」）
        from app.db.models import Result
        db_session.add(Result(project_id=pid, mode="forward", fp_version=1,
                              params_hash="abc", payload_json="{}", is_stale=False))
        db_session.commit()

        r = await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"city_rate.北京.dev": 50000},
        )
        assert r.status_code == 200
        # 重新查
        db_session.expire_all()
        rows = db_session.query(Result).filter_by(project_id=pid).all()
        assert all(row.is_stale for row in rows)


# ----- ISSUE-012: allocate 拒绝不存在的 project_id -----

async def test_allocate_unknown_project_404(client_factory):
    async with await client_factory() as client:
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


async def test_allocate_existing_project_still_works(client_factory):
    async with await client_factory() as client:
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
        assert len(r.json()["data"]["items"]) == 2  # v2.3: data is now {items, validation} envelope
