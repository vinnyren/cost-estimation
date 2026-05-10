"""ISSUE-010 regression: per-upload uuid prefix prevents collisions.

Round 1 QA missed this — two uploads sharing a basename (with the same or
different extension) silently clobbered each other's parsed-text file and
sometimes the original blob on disk. The fix lives in services/uploads.py:
each Upload row gets a 12-char uuid prefix on both the raw file and the
parsed-text mirror.
"""
from pathlib import Path
import uuid
import pytest
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
        rp = await c.post("/api/projects", headers=H, json={
            "name": "T", "project_type": "dev_only", "phase": "bidding",
            "city": "北京", "industry": "电子政务", "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
        })
        pid = rp.json()["data"]["id"]
        yield c, pid, tmp_path


async def _upload(c, pid, fixture_filename, post_filename):
    with open(FIX / fixture_filename, "rb") as f:
        return await c.post(
            f"/api/projects/{pid}/uploads",
            headers=H,
            files={"file": (post_filename, f, "application/octet-stream")},
        )


async def test_same_filename_uploaded_twice_does_not_overwrite(client_with_project):
    c, pid, tmp = client_with_project
    r1 = await _upload(c, pid, "sample.pdf", "needs.pdf")
    r2 = await _upload(c, pid, "sample.pdf", "needs.pdf")
    assert r1.status_code == 201 and r2.status_code == 201
    p1 = Path(r1.json()["data"]["parsed_text_path"])
    p2 = Path(r2.json()["data"]["parsed_text_path"])
    assert p1 != p2, "two uploads with same filename must produce different parsed paths"
    assert p1.exists() and p2.exists(), "both parsed-text files must persist"


async def test_same_basename_diff_extension_does_not_collide(client_with_project):
    c, pid, tmp = client_with_project
    r1 = await _upload(c, pid, "sample.pdf", "needs.pdf")
    r2 = await _upload(c, pid, "sample.docx", "needs.docx")
    assert r1.status_code == 201 and r2.status_code == 201
    p1 = Path(r1.json()["data"]["parsed_text_path"])
    p2 = Path(r2.json()["data"]["parsed_text_path"])
    assert p1 != p2
    # 两份 parsed 结果都还在
    assert p1.exists() and p2.exists()


async def test_uploaded_files_listed_separately(client_with_project):
    c, pid, _ = client_with_project
    await _upload(c, pid, "sample.pdf", "x.pdf")
    await _upload(c, pid, "sample.pdf", "x.pdf")
    r = await c.get(f"/api/projects/{pid}/uploads", headers=H)
    rows = r.json()["data"]
    assert len(rows) == 2
    parsed_paths = {row["parsed_text_path"] for row in rows}
    assert len(parsed_paths) == 2  # 两条记录指向独立文件


async def test_invalid_upload_does_not_leak_blob_on_disk(client_with_project, tmp_path):
    c, pid, tmp = client_with_project
    r = await c.post(
        f"/api/projects/{pid}/uploads",
        headers=H,
        files={"file": ("evil.exe", b"MZ\x90\x00not real", "application/octet-stream")},
    )
    assert r.status_code == 400
    # uploads dir 应当是空的（拒绝后清理）
    upload_dir = tmp / "uploads" / pid
    if upload_dir.exists():
        leftovers = list(upload_dir.iterdir())
        assert leftovers == [], f"rejected upload left blob on disk: {leftovers}"
