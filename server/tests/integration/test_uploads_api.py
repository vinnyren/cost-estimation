from pathlib import Path

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}
FIX = Path(__file__).parent.parent / "fixtures"


async def _make_project(c) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    return r.json()["data"]["id"]


async def test_upload_pdf(client_factory, tmp_data_dir):
    async with await client_factory() as c:
        pid = await _make_project(c)
        with open(FIX / "sample.pdf", "rb") as f:
            r = await c.post(f"/api/projects/{pid}/uploads", headers=H,
                              files={"file": ("report.pdf", f, "application/pdf")})
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["filetype"] == "pdf"
        assert data["size"] > 0


async def test_upload_invalid_extension_rejected(client_factory, tmp_data_dir):
    async with await client_factory() as c:
        pid = await _make_project(c)
        r = await c.post(f"/api/projects/{pid}/uploads", headers=H,
                          files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")})
        assert r.status_code == 400
        assert r.json()["detail"]["error"]["code"] == "INVALID_FILE_TYPE"


async def test_upload_then_list(client_factory, tmp_data_dir):
    async with await client_factory() as c:
        pid = await _make_project(c)
        with open(FIX / "sample.docx", "rb") as f:
            await c.post(f"/api/projects/{pid}/uploads", headers=H,
                          files={"file": ("needs.docx", f,
                                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
        r = await c.get(f"/api/projects/{pid}/uploads", headers=H)
        assert r.status_code == 200
        assert len(r.json()["data"]) == 1
