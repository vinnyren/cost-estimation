"""v2.5 — DELETE /api/projects/{pid}/uploads/{upload_id}."""
import pytest
from app.db.models import Project

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def _seed(db, pid="p-up-del"):
    p = Project(
        id=pid, name="upload del test",
        project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务",
        mode="forward", basis_data_ver="CSBMK-202510",
    )
    db.add(p)
    db.commit()
    return p


@pytest.mark.asyncio
async def test_delete_upload_removes_record_and_file(client_factory, db_session, tmp_path, monkeypatch):
    import app.services.uploads as uploads_mod
    monkeypatch.setattr(uploads_mod.settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(uploads_mod.settings, "parsed_dir", tmp_path / "parsed")

    _seed(db_session)
    async with await client_factory(seed_csbmk=False) as client:
        # 1. 上传一个文件
        files = {"file": ("hello.txt", b"hello world", "text/plain")}
        r = await client.post("/api/projects/p-up-del/uploads", headers=H, files=files)
        assert r.status_code == 201
        upload_id = r.json()["data"]["id"]

        # 2. 列表能看到
        r = await client.get("/api/projects/p-up-del/uploads", headers=H)
        assert r.status_code == 200
        assert len(r.json()["data"]) == 1

        # 3. 删除
        r = await client.delete(f"/api/projects/p-up-del/uploads/{upload_id}", headers=H)
        assert r.status_code == 204

        # 4. 列表为空
        r = await client.get("/api/projects/p-up-del/uploads", headers=H)
        assert len(r.json()["data"]) == 0


@pytest.mark.asyncio
async def test_delete_upload_returns_404_for_unknown_id(client_factory, db_session, tmp_path, monkeypatch):
    import app.services.uploads as uploads_mod
    monkeypatch.setattr(uploads_mod.settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(uploads_mod.settings, "parsed_dir", tmp_path / "parsed")

    _seed(db_session, pid="p-up-del-2")
    async with await client_factory(seed_csbmk=False) as client:
        r = await client.delete("/api/projects/p-up-del-2/uploads/99999", headers=H)
        assert r.status_code == 404
