"""Tests for POST /api/projects/{id}/functions/restore?version=N.

The restore endpoint replays a previously taken FPSnapshot back into the
function_points table. bulk_write already snapshots before mutation, so the
restore-cycle is: bulk_write v1 → bulk_write v2 → restore v1 → reads v1's data.
"""
H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        headers={**H, "Content-Type": "application/json"},
        json={
            "name": "qa-restore",
            "project_type": "dev_only",
            "mode": "forward",
            "city": "北京",
            "industry": "电子政务",
            "phase": "bidding",
            "basis_data_ver": "CSBMK®-202510",
        },
    )
    return r.json()["data"]["id"]


async def _bulk(client, pid, items, replace=False):
    return await client.post(
        f"/api/projects/{pid}/functions/bulk",
        headers={**H, "Content-Type": "application/json"},
        json={"items": items, "replace": replace},
    )


async def test_restore_replaces_current_with_snapshot(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        # v1: 1 个 FP
        await _bulk(client, pid, [
            {"name": "v1-only", "category": "EI", "complexity": "low",
             "ufp": 3, "us": 3, "source": "manual"},
        ], replace=True)

        # v2: 完全替换为 2 个不同 FP
        await _bulk(client, pid, [
            {"name": "v2-a", "category": "EQ", "complexity": "average",
             "ufp": 4, "us": 4, "source": "manual"},
            {"name": "v2-b", "category": "ILF", "complexity": "high",
             "ufp": 15, "us": 15, "source": "manual"},
        ], replace=True)

        cur = await client.get(f"/api/projects/{pid}/functions", headers=H)
        names_v2 = sorted([fp["name"] for fp in cur.json()["data"]])
        assert names_v2 == ["v2-a", "v2-b"]

        # restore 回 v1
        r = await client.post(
            f"/api/projects/{pid}/functions/restore?version=1",
            headers=H,
        )
        assert r.status_code == 200, r.text

        cur2 = await client.get(f"/api/projects/{pid}/functions", headers=H)
        names_after = [fp["name"] for fp in cur2.json()["data"]]
        assert names_after == ["v1-only"]


async def test_restore_unknown_version_404(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        await _bulk(client, pid, [
            {"name": "x", "category": "EI", "complexity": "low",
             "ufp": 3, "us": 3, "source": "manual"},
        ], replace=True)
        r = await client.post(
            f"/api/projects/{pid}/functions/restore?version=999",
            headers=H,
        )
        assert r.status_code == 404


async def test_restore_unknown_project_404(client_factory):
    async with await client_factory() as client:
        r = await client.post(
            "/api/projects/prj-nope/functions/restore?version=1",
            headers=H,
        )
        assert r.status_code == 404


async def test_list_snapshots_returns_metadata_only(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        await _bulk(client, pid, [
            {"name": "v1", "category": "EI", "complexity": "low",
             "ufp": 3, "us": 3, "source": "manual"},
        ], replace=True)
        await _bulk(client, pid, [
            {"name": "v2-a", "category": "EI", "complexity": "low",
             "ufp": 3, "us": 3, "source": "manual"},
            {"name": "v2-b", "category": "EI", "complexity": "low",
             "ufp": 3, "us": 3, "source": "manual"},
        ], replace=True)
        r = await client.get(f"/api/projects/{pid}/functions/snapshots", headers=H)
        assert r.status_code == 200
        snaps = r.json()["data"]
        # 至少 2 个快照（每次 bulk 写后产生）
        assert len(snaps) >= 2
        # 顶层字段齐全
        for s in snaps:
            assert "version" in s
            assert "snapshot_at" in s
            assert "fp_count" in s
            # snapshot_json 不暴露（响应应该精简）
            assert "snapshot_json" not in s
        # 最新快照 fp_count=2（v2 之后），更早的有 fp_count=1（v1）
        counts = [s["fp_count"] for s in snaps]
        assert 2 in counts and 1 in counts


async def test_list_snapshots_unknown_project_404(client_factory):
    async with await client_factory() as client:
        r = await client.get("/api/projects/prj-nope/functions/snapshots", headers=H)
        assert r.status_code == 404


async def test_restore_marks_results_stale(client_factory, db_session):
    """restore 后已有结果应被标记 stale，避免展示陈旧造价。"""
    async with await client_factory() as client:
        pid = await _make_project(client)
        await _bulk(client, pid, [
            {"name": "x", "category": "EI", "complexity": "low",
             "ufp": 3, "us": 3, "source": "manual"},
        ], replace=True)
        await _bulk(client, pid, [
            {"name": "y", "category": "EQ", "complexity": "high",
             "ufp": 6, "us": 6, "source": "manual"},
        ], replace=True)

        # 跑一次 forward 让 Result 行存在
        await client.post(
            "/api/calc/forward",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": pid},
        )

        # restore v1
        r = await client.post(
            f"/api/projects/{pid}/functions/restore?version=1",
            headers=H,
        )
        assert r.status_code == 200

        # 直接查 DB 确认 stale（db_session 看到与 API 同一 in-memory engine）
        from app.db.models import Result
        rows = db_session.query(Result).filter_by(project_id=pid).all()
        assert all(row.is_stale for row in rows)
