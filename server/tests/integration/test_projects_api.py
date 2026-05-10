import pytest
import uuid
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    db_file = f"/tmp/cost-test-{uuid.uuid4()}.sqlite"
    monkeypatch.setenv("COST_DB_PATH", db_file)
    # Force re-instantiation of settings & engine via reload of relevant modules.
    # Order matters: config first (settings singleton), then deps (rebinds settings ref
    # used by middleware), then db.session (rebuilds engine with new db_path), then main
    # (rebuilds app with refreshed routers + middleware).
    import importlib
    import app.config
    import app.deps
    import app.db.session
    import app.db.models
    import app.services.projects
    import app.api.projects
    importlib.reload(app.config)
    importlib.reload(app.deps)
    importlib.reload(app.db.session)
    importlib.reload(app.db.models)
    importlib.reload(app.services.projects)
    importlib.reload(app.api.projects)
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.main
    importlib.reload(app.main)
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_create_project_returns_id(client):
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


async def test_list_projects_after_create(client):
    await client.post("/api/projects", headers=H, json={
        "name": "P1", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    r = await client.get("/api/projects", headers=H)
    assert r.status_code == 200
    assert len(r.json()["data"]) >= 1


async def test_get_nonexistent_returns_404(client):
    r = await client.get("/api/projects/nonexistent", headers=H)
    assert r.status_code == 404
