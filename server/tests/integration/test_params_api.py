H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def test_global_params_after_seed(client_factory):
    async with await client_factory() as client:
        r = await client.get("/api/params/global", headers=H)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["city_rate"]["北京"]["dev"] == 33400
        assert data["productivity"]["dev"]["电子政务"]["P50"] == 8.02
        assert data["cf"]["bidding"] == 1.25


async def test_patch_global_param(client_factory):
    async with await client_factory() as client:
        r = await client.patch(
            "/api/params/global",
            headers={**H, "Content-Type": "application/json"},
            json={"key": "city_rate.北京.dev", "value": 33000})
        assert r.status_code == 200
        r2 = await client.get("/api/params/global", headers=H)
        assert r2.json()["data"]["city_rate"]["北京"]["dev"] == 33000
