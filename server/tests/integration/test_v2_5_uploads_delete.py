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


@pytest.mark.asyncio
async def test_delete_upload_does_not_remove_sibling_with_same_filename(
    client_factory, db_session, tmp_path, monkeypatch
):
    """/review F1: 同一项目两次上传同名文件，删一个不应误删另一个的磁盘文件。"""
    import app.services.uploads as uploads_mod
    monkeypatch.setattr(uploads_mod.settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(uploads_mod.settings, "parsed_dir", tmp_path / "parsed")

    _seed(db_session, pid="p-up-del-3")
    async with await client_factory(seed_csbmk=False) as client:
        # 上传两次同名 spec.txt
        files1 = {"file": ("spec.txt", b"version one", "text/plain")}
        r1 = await client.post("/api/projects/p-up-del-3/uploads", headers=H, files=files1)
        uid1 = r1.json()["data"]["id"]

        files2 = {"file": ("spec.txt", b"version two", "text/plain")}
        r2 = await client.post("/api/projects/p-up-del-3/uploads", headers=H, files=files2)
        uid2 = r2.json()["data"]["id"]

        # 磁盘上应有 2 个 spec.txt（不同 uid 前缀）
        upload_dir = tmp_path / "uploads" / "p-up-del-3"
        files_before = list(upload_dir.glob("*__spec.txt"))
        assert len(files_before) == 2, f"上传两次应有 2 个磁盘文件，实际 {len(files_before)}"

        # 删除第一个
        r = await client.delete(f"/api/projects/p-up-del-3/uploads/{uid1}", headers=H)
        assert r.status_code == 204

        # 第二个的磁盘文件必须仍存在 — 不应被 glob 误删
        files_after = list(upload_dir.glob("*__spec.txt"))
        assert len(files_after) == 1, f"删一个后应剩 1 个磁盘文件，实际 {len(files_after)}"

        # DB 中第二个记录也仍在
        r = await client.get("/api/projects/p-up-del-3/uploads", headers=H)
        remaining = r.json()["data"]
        assert len(remaining) == 1
        assert remaining[0]["id"] == uid2
