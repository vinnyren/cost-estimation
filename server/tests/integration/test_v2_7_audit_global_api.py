"""Integration tests for the global audit endpoint GET /api/audit (v2.7).

跨所有项目合并审计事件，按 ts/id 倒序，每条带 project_id + project_name。
"""

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def _make_project(c, name: str) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": name, "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    return r.json()["data"]["id"]


async def test_global_audit_empty_db_returns_empty_list(client_factory):
    async with await client_factory() as client:
        r = await client.get("/api/audit", headers=H)
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["error"] is None


async def test_global_audit_merges_events_across_projects(client_factory):
    async with await client_factory() as client:
        p1 = await _make_project(client, "项目甲")
        p2 = await _make_project(client, "项目乙")
        await client.patch(
            f"/api/projects/{p1}", headers={**H, "Content-Type": "application/json"},
            json={"name": "项目甲-改"})
        rows = (await client.get("/api/audit", headers=H)).json()["data"]
        pids = {r["project_id"] for r in rows}
        assert p1 in pids and p2 in pids
        names = {r["project_name"] for r in rows}
        assert "项目乙" in names
        ids = [r["id"] for r in rows]
        assert ids == sorted(ids, reverse=True)


async def test_global_audit_keyset_pagination(client_factory):
    async with await client_factory() as client:
        p1 = await _make_project(client, "P")
        for i in range(6):
            await client.patch(
                f"/api/projects/{p1}", headers={**H, "Content-Type": "application/json"},
                json={"name": f"P-{i}"})
        page1 = (await client.get("/api/audit?limit=3", headers=H)).json()["data"]
        assert len(page1) == 3
        last_id = page1[-1]["id"]
        page2 = (await client.get(
            f"/api/audit?limit=3&before_id={last_id}", headers=H)).json()["data"]
        assert all(r["id"] < last_id for r in page2)
