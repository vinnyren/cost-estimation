"""v2.2 — /api/projects/stats endpoint。"""
import pytest

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.mark.asyncio
async def test_stats_endpoint_returns_envelope(client_factory):
    async with await client_factory() as client:
        r = await client.get("/api/projects/stats", headers=H)
        assert r.status_code == 200
        body = r.json()
        assert "counts" in body
        assert "monthly_count" in body
        assert "monthly_p50_sum" in body
        assert "monthly_growth_pct" in body
        assert isinstance(body["counts"]["total"], int)


@pytest.mark.asyncio
async def test_stats_respects_month_query(client_factory):
    async with await client_factory() as client:
        r = await client.get("/api/projects/stats?month=2026-04", headers=H)
        assert r.status_code == 200
