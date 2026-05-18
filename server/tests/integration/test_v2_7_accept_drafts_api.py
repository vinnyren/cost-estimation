"""Integration tests for POST /api/projects/{id}/functions/accept-drafts (v2.7).

把项目内所有 source='claude_draft' 的功能点改为 source='ai_extracted'
（脱离草稿高亮），改动前存一次 FP 快照（reason=accept_drafts）。
"""

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}
HJ = {**H, "Content-Type": "application/json"}


async def _make_project(c) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    return r.json()["data"]["id"]


async def _add_fp(c, pid: str, name: str, source: str) -> None:
    await c.post(f"/api/projects/{pid}/functions", headers=HJ,
                 json={"name": name, "category": "EI", "complexity": "low",
                       "ufp": 3, "us": 3, "source": source})


async def test_accept_drafts_promotes_claude_draft_to_ai_extracted(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        await _add_fp(client, pid, "草稿1", "claude_draft")
        await _add_fp(client, pid, "草稿2", "claude_draft")
        await _add_fp(client, pid, "手工", "manual")
        r = await client.post(
            f"/api/projects/{pid}/functions/accept-drafts", headers=HJ)
        assert r.status_code == 200
        assert r.json()["data"]["accepted"] == 2
        fps = (await client.get(
            f"/api/projects/{pid}/functions", headers=H)).json()["data"]
        by_name = {f["name"]: f["source"] for f in fps}
        assert by_name["草稿1"] == "ai_extracted"
        assert by_name["草稿2"] == "ai_extracted"
        assert by_name["手工"] == "manual"


async def test_accept_drafts_creates_snapshot(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        await _add_fp(client, pid, "草稿1", "claude_draft")
        await client.post(
            f"/api/projects/{pid}/functions/accept-drafts", headers=HJ)
        snaps = (await client.get(
            f"/api/projects/{pid}/functions/snapshots", headers=H)).json()["data"]
        assert any(s["reason"] == "accept_drafts" for s in snaps)


async def test_accept_drafts_no_drafts_returns_zero(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        await _add_fp(client, pid, "手工", "manual")
        r = await client.post(
            f"/api/projects/{pid}/functions/accept-drafts", headers=HJ)
        assert r.status_code == 200
        assert r.json()["data"]["accepted"] == 0


async def test_accept_drafts_404_on_unknown_project(client_factory):
    async with await client_factory() as client:
        r = await client.post(
            "/api/projects/no-such-id/functions/accept-drafts", headers=HJ)
        assert r.status_code == 404
