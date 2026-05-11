"""ISSUE-020/021 regression: schema rejects NaN/Inf and negative inputs.

Round 3 QA found two latent footguns:
  - POST /api/calc/reverse with target_total="NaN" hit a 500 (NaN propagated
    deep into core/reverse and busted ZeroDivision-style logic).
  - bulk_write accepted ufp=-5/us=-5 → forward calc returned negative cost
    (cost_dev_yuan: -2283.83), an obviously wrong business result that no
    upstream gate caught.

The fix is in the schemas (functions.py + results.py): Field(ge=0) plus a
field_validator that rejects non-finite floats.
"""
H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def _make_reverse_project(c) -> str:
    rp = await c.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "reverse",
        "basis_data_ver": "CSBMK®-202510",
    })
    return rp.json()["data"]["id"]


async def test_negative_ufp_rejected_at_schema(client_factory):
    async with await client_factory() as c:
        pid = await _make_reverse_project(c)
        r = await c.post(
            f"/api/projects/{pid}/functions/bulk",
            headers={**H, "Content-Type": "application/json"},
            json={"items": [{"name": "x", "category": "EI", "complexity": "low",
                              "ufp": -5, "us": -5, "source": "manual"}]},
        )
        # Pydantic 拒绝 → 422
        assert r.status_code == 422
        body = r.json()
        msg = str(body)
        assert "ufp" in msg or "us" in msg
        assert "0" in msg  # ge=0 误差


async def test_negative_us_alone_rejected(client_factory):
    async with await client_factory() as c:
        pid = await _make_reverse_project(c)
        r = await c.post(
            f"/api/projects/{pid}/functions/bulk",
            headers={**H, "Content-Type": "application/json"},
            json={"items": [{"name": "x", "category": "EI", "complexity": "low",
                              "ufp": 3, "us": -1, "source": "manual"}]},
        )
        assert r.status_code == 422


async def test_zero_ufp_still_accepted_lower_bound(client_factory):
    """ge=0 — 0 仍然合法，避免破坏「占位 FP」用例。"""
    async with await client_factory() as c:
        pid = await _make_reverse_project(c)
        r = await c.post(
            f"/api/projects/{pid}/functions/bulk",
            headers={**H, "Content-Type": "application/json"},
            json={"items": [{"name": "x", "category": "EI", "complexity": "low",
                              "ufp": 0, "us": 0, "source": "manual"}]},
        )
        assert r.status_code == 201


async def test_reverse_target_nan_rejected_422_not_500(client_factory):
    async with await client_factory() as c:
        pid = await _make_reverse_project(c)
        r = await c.post(
            "/api/calc/reverse",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": pid, "target_total": "NaN", "other_cost": 0},
        )
        assert r.status_code == 422, f"NaN target should 422, got {r.status_code} ({r.text})"


async def test_reverse_target_inf_rejected_422(client_factory):
    async with await client_factory() as c:
        pid = await _make_reverse_project(c)
        r = await c.post(
            "/api/calc/reverse",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": pid, "target_total": "Infinity", "other_cost": 0},
        )
        assert r.status_code == 422


async def test_reverse_target_zero_rejected_at_schema(client_factory):
    """gt=0 — 0 元目标无业务意义，schema 层先拒一道。"""
    async with await client_factory() as c:
        pid = await _make_reverse_project(c)
        r = await c.post(
            "/api/calc/reverse",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": pid, "target_total": 0, "other_cost": 0},
        )
        assert r.status_code == 422


async def test_forward_negative_other_cost_rejected(client_factory):
    async with await client_factory() as c:
        pid = await _make_reverse_project(c)
        # 加一个合法 FP 才能跑 forward
        await c.post(
            f"/api/projects/{pid}/functions/bulk",
            headers={**H, "Content-Type": "application/json"},
            json={"items": [{"name": "x", "category": "EI", "complexity": "low",
                              "ufp": 3, "us": 3, "source": "manual"}]},
        )
        r = await c.post(
            "/api/calc/forward",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": pid, "other_cost": -100},
        )
        assert r.status_code == 422
