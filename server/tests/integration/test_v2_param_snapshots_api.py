"""Integration tests for /api/params/snapshots (v2.0 GAP-H, Task T4).

ParamSnapshot 4-endpoint surface — create / list / restore / delete. Restore
must bring back the parameter state captured at snapshot time, even after
intervening mutations.
"""

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def test_create_global_snapshot_then_list(client_factory):
    async with await client_factory() as client:
        r = await client.post(
            "/api/params/snapshots",
            headers=H,
            json={"scope": "global", "label": "实验前 baseline"},
        )
        assert r.status_code == 201
        snap_id = r.json()["data"]["id"]
        r2 = await client.get("/api/params/snapshots?scope=global", headers=H)
        assert r2.status_code == 200
        rows = r2.json()["data"]
        assert any(
            s["id"] == snap_id and s["label"] == "实验前 baseline" for s in rows
        )


async def test_restore_snapshot_brings_back_old_value(client_factory):
    async with await client_factory() as client:
        # 1) 改一个全局参数让它偏离 baseline
        r0 = await client.patch(
            "/api/params/global",
            headers={**H, "Content-Type": "application/json"},
            json={"key": "hours_per_pm", "value": 200},
        )
        assert r0.status_code == 200
        # 2) 快照 baseline-after-change
        r = await client.post(
            "/api/params/snapshots",
            headers=H,
            json={"scope": "global", "label": "after-change"},
        )
        snap_id = r.json()["data"]["id"]
        # 3) 改第二次
        r1 = await client.patch(
            "/api/params/global",
            headers={**H, "Content-Type": "application/json"},
            json={"key": "hours_per_pm", "value": 300},
        )
        assert r1.status_code == 200
        # 4) restore 到 200 那一刻
        r3 = await client.post(
            f"/api/params/snapshots/{snap_id}/restore", headers=H
        )
        assert r3.status_code == 200
        eff = (await client.get("/api/params/effective", headers=H)).json()["data"]
        assert eff["hours_per_pm"] == 200


async def test_delete_snapshot(client_factory):
    async with await client_factory() as client:
        r = await client.post(
            "/api/params/snapshots", headers=H, json={"scope": "global"}
        )
        snap_id = r.json()["data"]["id"]
        r2 = await client.delete(
            f"/api/params/snapshots/{snap_id}", headers=H
        )
        assert r2.status_code == 204
        rows = (
            await client.get("/api/params/snapshots?scope=global", headers=H)
        ).json()["data"]
        assert all(s["id"] != snap_id for s in rows)


async def test_restore_404_on_unknown_snapshot(client_factory):
    async with await client_factory() as client:
        r = await client.post("/api/params/snapshots/99999/restore", headers=H)
        assert r.status_code == 404
