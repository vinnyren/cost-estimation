import pytest, uuid
from pathlib import Path
from httpx import AsyncClient, ASGITransport

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}
FIX = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def client_with_project(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    db_file = f"/tmp/cost-test-{uuid.uuid4()}.sqlite"
    monkeypatch.setenv("COST_DB_PATH", db_file)
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.projects", "app.services.calc",
              "app.services.uploads",
              "app.api.projects", "app.api.params", "app.api.calc",
              "app.api.uploads", "app.api.health", "app.main"]:
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


async def test_upload_pdf(client_with_project):
    c, pid = client_with_project
    with open(FIX / "sample.pdf", "rb") as f:
        r = await c.post(f"/api/projects/{pid}/uploads", headers=H,
                          files={"file": ("report.pdf", f, "application/pdf")})
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["filetype"] == "pdf"
    assert data["size"] > 0


async def test_upload_invalid_extension_rejected(client_with_project):
    c, pid = client_with_project
    r = await c.post(f"/api/projects/{pid}/uploads", headers=H,
                      files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")})
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "INVALID_FILE_TYPE"


async def test_upload_then_list(client_with_project):
    c, pid = client_with_project
    with open(FIX / "sample.docx", "rb") as f:
        await c.post(f"/api/projects/{pid}/uploads", headers=H,
                      files={"file": ("needs.docx", f,
                                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    r = await c.get(f"/api/projects/{pid}/uploads", headers=H)
    assert r.status_code == 200
    assert len(r.json()["data"]) == 1
