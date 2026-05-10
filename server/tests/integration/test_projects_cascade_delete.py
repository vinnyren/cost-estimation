"""Integration: deleting a project with FP/snapshot/result rows must cascade.

Regression for the HIGH bug found in plan-4 review: services.projects.delete()
calls db.delete(p); db.commit() with no cascade, and PRAGMA foreign_keys=ON in
session.py raised IntegrityError → 500 when the user pressed "delete" on a
project that already had function points or other child rows.

Fix lives in models.py (relationship cascade + FK ondelete CASCADE). This test
exercises the API surface end-to-end so an accidental rollback would fail here.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}

SAMPLE_FP = {
    "name": "门户首页",
    "category": "EQ",
    "complexity": "low",
    "ufp": 4.0,
    "us": 4.0,
    "subsystem": "政务平台",
    "l2_module": "首页",
}


@pytest.fixture
async def client_with_project(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    db_file = f"/tmp/cost-test-{uuid.uuid4()}.sqlite"
    monkeypatch.setenv("COST_DB_PATH", db_file)
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in [
        "app.config", "app.db.session", "app.deps", "app.db.models",
        "app.services.params", "app.services.projects", "app.services.calc",
        "app.services.uploads", "app.services.functions",
        "app.api.projects", "app.api.params", "app.api.calc",
        "app.api.uploads", "app.api.functions",
        "app.api.health", "app.main",
    ]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/projects", headers=H, json={
            "name": "cascade-test",
            "project_type": "dev_only",
            "phase": "bidding",
            "city": "北京",
            "industry": "电子政务",
            "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
        })
        pid = r.json()["data"]["id"]
        yield c, pid, engine


async def test_delete_project_with_fps_cascades(client_with_project):
    """Project with FP rows: DELETE should succeed (no IntegrityError) and
    purge child rows."""
    c, pid, engine = client_with_project

    # Seed 3 FP rows via the bulk endpoint (matches what the UI does).
    items = [{**SAMPLE_FP, "name": f"Item-{i}"} for i in range(3)]
    r = await c.post(
        f"/api/projects/{pid}/functions/bulk",
        headers={**H, "Content-Type": "application/json"},
        json={"items": items, "replace": True},
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["written"] == 3

    # Sanity: rows present before delete.
    list_r = await c.get(f"/api/projects/{pid}/functions", headers=H)
    assert list_r.status_code == 200
    assert len(list_r.json()["data"]) == 3

    # The bug: this used to raise IntegrityError → 500. With cascade it must 200.
    del_r = await c.delete(f"/api/projects/{pid}", headers=H)
    assert del_r.status_code in (200, 204), del_r.text

    # Project gone.
    get_r = await c.get(f"/api/projects/{pid}", headers=H)
    assert get_r.status_code == 404

    # Child rows gone (verify directly against the DB so we don't rely on the
    # functions list endpoint behavior for orphaned project ids).
    with engine.connect() as conn:
        fp_rows = conn.execute(
            text("SELECT COUNT(*) FROM function_points WHERE project_id = :pid"),
            {"pid": pid},
        ).scalar_one()
        assert fp_rows == 0, "FP rows must be cascade-deleted"


async def test_delete_project_with_snapshot_cascades(client_with_project):
    """Project with FP + snapshot (snapshots are written by the bulk replace
    trigger): DELETE must purge snapshots too."""
    c, pid, engine = client_with_project

    # Two bulk replaces → at least one snapshot row.
    for batch in range(2):
        items = [{**SAMPLE_FP, "name": f"v{batch}-{i}"} for i in range(2)]
        r = await c.post(
            f"/api/projects/{pid}/functions/bulk",
            headers={**H, "Content-Type": "application/json"},
            json={"items": items, "replace": True},
        )
        assert r.status_code == 201, r.text

    with engine.connect() as conn:
        snap_before = conn.execute(
            text("SELECT COUNT(*) FROM fp_snapshots WHERE project_id = :pid"),
            {"pid": pid},
        ).scalar_one()
        assert snap_before >= 1, "fixture should have written at least one snapshot"

    del_r = await c.delete(f"/api/projects/{pid}", headers=H)
    assert del_r.status_code in (200, 204), del_r.text

    with engine.connect() as conn:
        snap_after = conn.execute(
            text("SELECT COUNT(*) FROM fp_snapshots WHERE project_id = :pid"),
            {"pid": pid},
        ).scalar_one()
        assert snap_after == 0, "snapshots must be cascade-deleted"


async def test_delete_empty_project_still_works(client_with_project):
    """No regression for the simple path: an empty project should still
    delete cleanly."""
    c, pid, _engine = client_with_project
    del_r = await c.delete(f"/api/projects/{pid}", headers=H)
    assert del_r.status_code in (200, 204), del_r.text
    get_r = await c.get(f"/api/projects/{pid}", headers=H)
    assert get_r.status_code == 404


async def test_delete_project_removes_disk_dirs(client_with_project, tmp_path):
    """回归 v1.1 polish 发现的 LOW-MEDIUM bug：旧版 services.projects.delete
    只删 DB 行，不清理磁盘 uploads/<pid>/、parsed/<pid>/、exports/<pid>/。
    修法：在 cascade 之前 shutil.rmtree(target, ignore_errors=True)。

    本测试用 fixture 中已设置的 COST_DATA_DIR=tmp_path 推断 settings.upload_dir
    等派生路径，手工预置目录后调用 DELETE，断言目录消失。
    """
    c, pid, _engine = client_with_project

    # fixture 中 COST_DATA_DIR=tmp_path（参见上方 fixture）。派生路径：
    #   uploads = tmp_path / "uploads"
    #   parsed  = tmp_path / "parsed"
    #   exports = tmp_path / "exports"
    upload_dir = tmp_path / "uploads" / pid
    parsed_dir = tmp_path / "parsed" / pid
    export_dir = tmp_path / "exports" / pid
    for d in (upload_dir, parsed_dir, export_dir):
        d.mkdir(parents=True, exist_ok=True)
        (d / "demo.txt").write_text("dummy", encoding="utf-8")
    assert upload_dir.exists() and parsed_dir.exists() and export_dir.exists()

    del_r = await c.delete(f"/api/projects/{pid}", headers=H)
    assert del_r.status_code in (200, 204), del_r.text

    # 物理目录与孤儿文件已清理
    assert not upload_dir.exists(), "uploads/<pid>/ 应被 delete 服务清理"
    assert not parsed_dir.exists(), "parsed/<pid>/ 应被 delete 服务清理"
    assert not export_dir.exists(), "exports/<pid>/ 应被 delete 服务清理"
