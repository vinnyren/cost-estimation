H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


SAMPLE_FP = {
    "name": "门户首页", "category": "EQ", "complexity": "low",
    "ufp": 4.0, "us": 4.0, "subsystem": "政务平台", "l2_module": "首页",
}


async def _make_project(c) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    return r.json()["data"]["id"]


async def test_create_fp(client_factory):
    async with await client_factory() as c:
        pid = await _make_project(c)
        r = await c.post(f"/api/projects/{pid}/functions",
                          headers={**H, "Content-Type": "application/json"},
                          json=SAMPLE_FP)
        assert r.status_code == 201
        assert r.json()["data"]["category"] == "EQ"


async def test_bulk_replace(client_factory):
    async with await client_factory() as c:
        pid = await _make_project(c)
        items = [{**SAMPLE_FP, "name": f"Item-{i}"} for i in range(5)]
        r = await c.post(f"/api/projects/{pid}/functions/bulk",
                          headers={**H, "Content-Type": "application/json"},
                          json={"items": items, "replace": True})
        assert r.status_code == 201
        assert r.json()["data"]["written"] == 5

        r2 = await c.get(f"/api/projects/{pid}/functions", headers=H)
        assert len(r2.json()["data"]) == 5


async def test_bulk_accepts_ai_extracted_source(client_factory):
    """Cross-plan alignment: SKILL/AI agents write source='ai_extracted'.

    Backend Pydantic schema must accept this value (regression for the
    422 bug where the old Literal only allowed claude_draft|manual|imported|allocator).
    """
    async with await client_factory() as c:
        pid = await _make_project(c)
        items = [{**SAMPLE_FP, "name": "AI-Extracted-FP", "source": "ai_extracted"}]
        r = await c.post(f"/api/projects/{pid}/functions/bulk",
                          headers={**H, "Content-Type": "application/json"},
                          json={"items": items, "replace": True})
        assert r.status_code in (200, 201), r.text
        assert r.json()["data"]["written"] == 1

        r2 = await c.get(f"/api/projects/{pid}/functions", headers=H)
        rows = r2.json()["data"]
        assert len(rows) == 1
        assert rows[0]["source"] == "ai_extracted"


async def test_patch_fp_marks_results_stale(client_factory):
    async with await client_factory() as c:
        pid = await _make_project(c)
        r = await c.post(f"/api/projects/{pid}/functions",
                          headers={**H, "Content-Type": "application/json"},
                          json=SAMPLE_FP)
        fp_id = r.json()["data"]["id"]
        r2 = await c.patch(f"/api/projects/{pid}/functions/{fp_id}",
                            headers={**H, "Content-Type": "application/json"},
                            json={"complexity": "high", "ufp": 7.0})
        assert r2.status_code == 200
        assert r2.json()["data"]["complexity"] == "high"
