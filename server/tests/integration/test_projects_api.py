H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def test_create_project_returns_id(client_factory):
    async with await client_factory() as client:
        r = await client.post("/api/projects", headers=H, json={
            "name": "测试项目",
            "project_type": "dev_only",
            "phase": "bidding",
            "city": "北京",
            "industry": "电子政务",
            "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
        })
        assert r.status_code == 201
        body = r.json()["data"]
        assert "id" in body
        assert body["name"] == "测试项目"


async def test_list_projects_after_create(client_factory):
    async with await client_factory() as client:
        await client.post("/api/projects", headers=H, json={
            "name": "P1", "project_type": "dev_only", "phase": "bidding",
            "city": "北京", "industry": "电子政务", "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
        })
        r = await client.get("/api/projects", headers=H)
        assert r.status_code == 200
        assert len(r.json()["data"]) >= 1


async def test_get_nonexistent_returns_404(client_factory):
    async with await client_factory() as client:
        r = await client.get("/api/projects/nonexistent", headers=H)
        assert r.status_code == 404
