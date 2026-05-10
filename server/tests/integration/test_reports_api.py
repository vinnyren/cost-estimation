import pytest
import uuid
from io import BytesIO
from httpx import AsyncClient, ASGITransport
from openpyxl import load_workbook

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


@pytest.fixture
async def client_with_fp(monkeypatch, tmp_path):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    monkeypatch.setenv("COST_DB_PATH", f"/tmp/cost-test-{uuid.uuid4()}.sqlite")
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    import importlib
    for m in ["app.config", "app.db.session", "app.deps", "app.db.models",
              "app.services.params", "app.services.projects", "app.services.calc",
              "app.services.uploads", "app.services.functions", "app.services.reports",
              "app.exporters.excel",
              "app.api.projects", "app.api.params", "app.api.calc",
              "app.api.uploads", "app.api.functions", "app.api.reports",
              "app.api.health", "app.main"]:
        importlib.reload(importlib.import_module(m))
    from app.db.session import Base, engine
    Base.metadata.create_all(bind=engine)
    import app.services.params
    app.services.params.seed_from_csbmk()
    import app.main
    transport = ASGITransport(app=app.main.create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # 建项目
        rp = await c.post("/api/projects", headers=H, json={
            "name": "T", "project_type": "dev_only", "phase": "bidding",
            "city": "北京", "industry": "电子政务", "mode": "forward",
            "basis_data_ver": "CSBMK®-202510",
        })
        pid = rp.json()["data"]["id"]
        # 加 FP
        await c.post(f"/api/projects/{pid}/functions",
                     headers={**H, "Content-Type": "application/json"},
                     json={"name": "首页", "category": "EQ", "complexity": "low",
                           "ufp": 4.0, "us": 4.0})
        yield c, pid


async def test_download_excel(client_with_fp):
    c, pid = client_with_fp
    r = await c.get(f"/api/reports/excel/{pid}", headers=H)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    wb = load_workbook(BytesIO(r.content))
    # 必备 7 Sheet
    for s in ["封面声明", "评估结果摘要", "评估报告书", "调整因子表",
              "功能点计数表", "详细计算过程", "参数附录"]:
        assert s in wb.sheetnames
    # 摘要值
    summary = wb["评估结果摘要"]
    # us=4 * cf=1.21 = 4.84
    assert summary["C2"].value == 4.84


async def test_download_no_fp_returns_400(client_with_fp):
    c, pid = client_with_fp
    # 删掉刚加的 FP
    fps_r = await c.get(f"/api/projects/{pid}/functions", headers=H)
    fp_id = fps_r.json()["data"][0]["id"]
    await c.delete(f"/api/projects/{pid}/functions/{fp_id}", headers=H)
    r = await c.get(f"/api/reports/excel/{pid}", headers=H)
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "FP_EMPTY"
