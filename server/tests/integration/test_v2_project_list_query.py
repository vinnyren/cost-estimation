"""Integration tests for GET /api/projects query params.

Task T6 (v2.0 gap-closure) — GAP-F. The list endpoint must support:
  - q (substring on name, case-insensitive)
  - city / industry / phase / mode filters (exact match)
  - sort + order (created_at | updated_at | name | target_cost; asc | desc)
  - page + size pagination (size capped at 200)
  - meta envelope: {total, page, size}
"""

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def _seed_projects(c) -> None:
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


async def test_list_no_query_returns_all_paginated(client_factory):
    async with await client_factory() as client:
        await _seed_projects(client)
        r = (await client.get("/api/projects", headers=H)).json()
        assert r["success"]
        assert len(r["data"]) == 4
        assert r["meta"]["total"] == 4
        assert r["meta"]["page"] == 1


async def test_list_q_substring_match(client_factory):
    async with await client_factory() as client:
        await _seed_projects(client)
        r = (await client.get("/api/projects?q=智慧", headers=H)).json()
        names = [p["name"] for p in r["data"]]
        assert "智慧政务-2026" in names
        assert "智慧交通" in names
        assert "电力调度" not in names
        assert r["meta"]["total"] == 2


async def test_list_filter_by_city(client_factory):
    async with await client_factory() as client:
        await _seed_projects(client)
        r = (await client.get("/api/projects?city=北京", headers=H)).json()
        assert r["meta"]["total"] == 2
        assert all(p["city"] == "北京" for p in r["data"])


async def test_list_filter_by_industry(client_factory):
    async with await client_factory() as client:
        await _seed_projects(client)
        r = (await client.get("/api/projects?industry=电子政务", headers=H)).json()
        assert r["meta"]["total"] == 2


async def test_list_sort_by_name_asc(client_factory):
    async with await client_factory() as client:
        await _seed_projects(client)
        r = (await client.get("/api/projects?sort=name&order=asc", headers=H)).json()
        names = [p["name"] for p in r["data"]]
        assert names == sorted(names)


async def test_list_pagination_size_2(client_factory):
    async with await client_factory() as client:
        await _seed_projects(client)
        r1 = (await client.get("/api/projects?size=2&page=1", headers=H)).json()
        assert len(r1["data"]) == 2
        r2 = (await client.get("/api/projects?size=2&page=2", headers=H)).json()
        assert len(r2["data"]) == 2
        assert {p["id"] for p in r1["data"]}.isdisjoint({p["id"] for p in r2["data"]})


async def test_list_size_capped_at_200(client_factory):
    async with await client_factory() as client:
        await _seed_projects(client)
        r = await client.get("/api/projects?size=500", headers=H)
        if r.status_code == 200:
            assert r.json()["meta"]["size"] <= 200
        else:
            assert r.status_code == 422
