import pytest
import uuid
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client_with_project(monkeypatch):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    db_file = f"/tmp/cost-test-{uuid.uuid4()}.sqlite"
    monkeypatch.setenv("COST_DB_PATH", db_file)
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.projects", "app.services.calc",
              "app.api.projects", "app.api.params", "app.api.calc",
              "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/projects", headers=H, json={
            "name": "T", "project_type": "dev_only", "phase": "bidding",
            "city": "北京", "industry": "电子政务", "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
        })
        pid = r.json()["data"]["id"]
        yield c, pid


async def test_forward_endpoint_smoke(client_with_project):
    c, pid = client_with_project
    r = await c.post(
        "/api/calc/forward",
        headers={**H, "Content-Type": "application/json"},
        json={"project_id": pid, "items": [{"us": 275}],
              "dev_factor": 1.0, "include_dev": True})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["scale_us"] == 275
    assert abs(data["scale_adjusted"] - 275 * 1.21) < 1e-6
