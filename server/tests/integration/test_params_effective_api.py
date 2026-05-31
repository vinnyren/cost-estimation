"""Tests for /api/projects/{id}/params/effective + override + reset.

These endpoints feed the ParamManager view. Effective response is FLAT-named
(productivity_dev / productivity_ops / factors_dev / factors_ops) so override
keys traverse the same tree as the response, while /api/params/global stays
nested for backward compat with existing seeded-params tests.
"""
import pytest

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def _make_project(client) -> str:
    r = await client.post(
        "/api/projects",
        headers={**H, "Content-Type": "application/json"},
        json={
            "name": "qa-eff",
            "project_type": "dev_only",
            "mode": "forward",
            "city": "北京",
            "industry": "电子政务",
            "phase": "bidding",
            "basis_data_ver": "CSBMK®-202510",
        },
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["data"]["id"]


async def test_effective_returns_flat_keys_with_overrides_empty(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        r = await client.get(f"/api/projects/{pid}/params/effective", headers=H)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert "productivity_dev" in data
        assert "productivity_ops" in data
        assert "city_rate" in data
        assert "factors_dev" in data
        assert "factors_ops" in data
        assert data["cf"]["bidding"] == 1.25
        assert data["productivity_dev"]["电子政务"]["P50"] == 8.02
        assert data["city_rate"]["北京"]["dev"] == 33400
        assert data["overrides"] == {}


async def test_effective_404_for_missing_project(client_factory):
    async with await client_factory() as client:
        r = await client.get(
            "/api/projects/prj-does-not-exist/params/effective", headers=H
        )
        assert r.status_code == 404


async def test_override_applies_and_appears_in_effective(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        r = await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"city_rate.北京.dev": 99999},
        )
        assert r.status_code == 200, r.text
        body = r.json()["data"]
        assert body["overrides"]["city_rate.北京.dev"] == 99999
        assert body["city_rate"]["北京"]["dev"] == 99999

        # GET 也应当看到
        g = await client.get(f"/api/projects/{pid}/params/effective", headers=H)
        assert g.json()["data"]["city_rate"]["北京"]["dev"] == 99999


async def test_override_supports_productivity_flat_path(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        r = await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"productivity_dev.电子政务.P50": 9.99},
        )
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["productivity_dev"]["电子政务"]["P50"] == 9.99
        # 其它 band 不被波及
        assert body["productivity_dev"]["电子政务"]["P10"] == 2.26


async def test_override_clear_via_null(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"city_rate.北京.dev": 99999},
        )
        # 用 null 撤销 override
        r = await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"city_rate.北京.dev": None},
        )
        assert r.status_code == 200
        body = r.json()["data"]
        assert "city_rate.北京.dev" not in body["overrides"]
        assert body["city_rate"]["北京"]["dev"] == 33400  # 回到 global 值


async def test_global_reset_clears_modified_and_reseeds(client_factory):
    async with await client_factory() as client:
        # 先 patch global 让 modified=true
        await client.patch(
            "/api/params/global",
            headers={**H, "Content-Type": "application/json"},
            json={"key": "city_rate.北京.dev", "value": 11111},
        )
        g1 = await client.get("/api/params/global", headers=H)
        assert g1.json()["data"]["city_rate"]["北京"]["dev"] == 11111

        r = await client.post("/api/params/global/reset", headers=H)
        assert r.status_code == 200, r.text

        g2 = await client.get("/api/params/global", headers=H)
        assert g2.json()["data"]["city_rate"]["北京"]["dev"] == 33400  # 回 seed


async def test_calc_forward_uses_overrides(client_factory):
    """端到端：override 后 calc 结果应该跟着变。"""
    async with await client_factory() as client:
        pid = await _make_project(client)
        # 加 1 个 FP
        await client.post(
            f"/api/projects/{pid}/functions/bulk",
            headers={**H, "Content-Type": "application/json"},
            json={"items": [{"name": "x", "category": "EI", "complexity": "low",
                              "ufp": 3, "us": 3, "source": "manual"}]},
        )
        # 基线
        r1 = await client.post(
            "/api/calc/forward",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": pid},
        )
        assert r1.status_code == 200
        base_cost = r1.json()["data"]["cost_dev_yuan"]["P50"]

        # 把 北京 dev 费率翻倍 → cost_dev_yuan.P50 应当大致翻倍
        await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"city_rate.北京.dev": 66800},
        )
        r2 = await client.post(
            "/api/calc/forward",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": pid},
        )
        assert r2.status_code == 200
        new_cost = r2.json()["data"]["cost_dev_yuan"]["P50"]
        assert new_cost == pytest.approx(2 * base_cost, rel=1e-6)


async def test_override_404_for_missing_project(client_factory):
    async with await client_factory() as client:
        r = await client.patch(
            "/api/projects/prj-nope/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"city_rate.北京.dev": 1},
        )
        assert r.status_code == 404
