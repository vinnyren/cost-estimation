"""Integration tests for GET /api/projects query params.

Task T6 (v2.0 gap-closure) — GAP-F. The list endpoint must support:
  - q (substring on name, case-insensitive)
  - city / industry / phase / mode filters (exact match)
  - sort + order (created_at | updated_at | name | target_cost; asc | desc)
  - page + size pagination (size capped at 200)
  - meta envelope: {total, page, size}
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.projects",
              "app.api.projects", "app.api.params", "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        for spec in [
            ("智慧政务-2026", "北京", "电子政务", "bidding"),
            ("电力调度", "上海", "电力", "planning"),
            ("智慧交通", "北京", "交通", "settled"),
            ("税务系统", "广州", "电子政务", "budget"),
        ]:
            await c.post("/api/projects", headers=H, json={
                "name": spec[0], "city": spec[1], "industry": spec[2], "phase": spec[3],
                "project_type": "dev_only", "mode": "forward",
                "basis_data_ver": "CSBMK®-202510",
            })
        yield c


async def test_list_no_query_returns_all_paginated(client):
    r = (await client.get("/api/projects", headers=H)).json()
    assert r["success"]
    assert len(r["data"]) == 4
    assert r["meta"]["total"] == 4
    assert r["meta"]["page"] == 1


async def test_list_q_substring_match(client):
    r = (await client.get("/api/projects?q=智慧", headers=H)).json()
    names = [p["name"] for p in r["data"]]
    assert "智慧政务-2026" in names
    assert "智慧交通" in names
    assert "电力调度" not in names
    assert r["meta"]["total"] == 2


async def test_list_filter_by_city(client):
    r = (await client.get("/api/projects?city=北京", headers=H)).json()
    assert r["meta"]["total"] == 2
    assert all(p["city"] == "北京" for p in r["data"])


async def test_list_filter_by_industry(client):
    r = (await client.get("/api/projects?industry=电子政务", headers=H)).json()
    assert r["meta"]["total"] == 2


async def test_list_sort_by_name_asc(client):
    r = (await client.get("/api/projects?sort=name&order=asc", headers=H)).json()
    names = [p["name"] for p in r["data"]]
    assert names == sorted(names)


async def test_list_pagination_size_2(client):
    r1 = (await client.get("/api/projects?size=2&page=1", headers=H)).json()
    assert len(r1["data"]) == 2
    r2 = (await client.get("/api/projects?size=2&page=2", headers=H)).json()
    assert len(r2["data"]) == 2
    assert {p["id"] for p in r1["data"]}.isdisjoint({p["id"] for p in r2["data"]})


async def test_list_size_capped_at_200(client):
    r = await client.get("/api/projects?size=500", headers=H)
    if r.status_code == 200:
        assert r.json()["meta"]["size"] <= 200
    else:
        assert r.status_code == 422
