import pytest
import uuid
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    db_file = f"/tmp/cost-test-{uuid.uuid4()}.sqlite"
    monkeypatch.setenv("COST_DB_PATH", db_file)
    import importlib
    import app.config
    importlib.reload(app.config)
    import app.db.session
    importlib.reload(app.db.session)
    import app.deps
    importlib.reload(app.deps)
    import app.db.models
    importlib.reload(app.db.models)
    import app.services.params
    importlib.reload(app.services.params)
    import app.services.projects
    importlib.reload(app.services.projects)
    import app.api.projects
    importlib.reload(app.api.projects)
    import app.api.params
    importlib.reload(app.api.params)
    import app.api.health
    importlib.reload(app.api.health)
    import app.main
    importlib.reload(app.main)
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    # 显式 seed（startup hook 在 ASGITransport lifespan 才触发）
    app.services.params.seed_from_csbmk()
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_global_params_after_seed(client):
    r = await client.get("/api/params/global", headers=H)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["city_rate"]["北京"]["dev"] == 32198
    assert data["productivity"]["dev"]["电子政务"]["P50"] == 6.41
    assert data["cf"]["bidding"] == 1.21


async def test_patch_global_param(client):
    r = await client.patch(
        "/api/params/global",
        headers={**H, "Content-Type": "application/json"},
        json={"key": "city_rate.北京.dev", "value": 33000})
    assert r.status_code == 200
    r2 = await client.get("/api/params/global", headers=H)
    assert r2.json()["data"]["city_rate"]["北京"]["dev"] == 33000
