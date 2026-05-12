"""v2.5 — /api/params/factor-meta endpoint."""
import pytest

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.mark.asyncio
async def test_factor_meta_returns_dev_and_ops(client_factory):
    async with await client_factory() as client:
        r = await client.get("/api/params/factor-meta", headers=H)
        assert r.status_code == 200
        body = r.json()
        assert "factors_dev" in body
        assert "factors_ops" in body
        assert "app_type" in body["factors_dev"]
        assert body["factors_dev"]["app_type"]["label"] == "应用类型"


@pytest.mark.asyncio
async def test_factor_meta_options_have_label_and_description(client_factory):
    async with await client_factory() as client:
        r = await client.get("/api/params/factor-meta", headers=H)
        body = r.json()
        app_type_opts = body["factors_dev"]["app_type"]["options"]
        assert "业务处理" in app_type_opts
        assert "label" in app_type_opts["业务处理"]
        assert "description" in app_type_opts["业务处理"]
