"""v2.8 — reverse_fill AI 任务：创建 + 状态机 + 缺口分摊。"""
import pytest
from app.db.models import Project, FunctionPoint

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def _seed(db, pid="p-revfill"):
    p = Project(id=pid, name="reverse fill",
                project_type="dev_only", phase="bidding",
                city="北京", industry="电子政务",
                mode="reverse", basis_data_ver="CSBMK-202510",
                target_cost=1000000)
    db.add(p)
    db.add(FunctionPoint(id="fp-seed-1", project_id=pid, version=1,
                         subsystem="结算", l1_module="资金", l2_module="查询",
                         category="EQ", complexity="average",
                         modify_type="add", ufp=4, us=4, source="manual"))
    db.commit()
    return p


@pytest.mark.asyncio
async def test_create_reverse_fill_task(client_factory, db_session):
    _seed(db_session)
    async with await client_factory() as client:
        r = await client.post("/api/ai-tasks", headers=H,
                               json={"project_id": "p-revfill", "kind": "reverse_fill"})
        assert r.status_code == 201
        body = r.json()
        assert body["kind"] == "reverse_fill"
        assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_reverse_fill_task_progress_flow(client_factory, db_session):
    """模拟 cost-fill 插件的进度上报序列。"""
    _seed(db_session, pid="p-revfill-2")
    async with await client_factory() as client:
        r = await client.post("/api/ai-tasks", headers=H,
                               json={"project_id": "p-revfill-2", "kind": "reverse_fill"})
        task_id = r.json()["id"]
        for pct, log in [
            (15, "✓ 加载反算模块树"),
            (45, "✓ 计算各叶子缺口"),
            (80, "✓ 生成补全 FP 草稿"),
        ]:
            r = await client.patch(f"/api/ai-tasks/{task_id}", headers=H,
                                   json={"status": "running", "progress_pct": pct,
                                         "stage_log_append": log})
            assert r.status_code == 200
        r = await client.patch(f"/api/ai-tasks/{task_id}", headers=H,
                               json={"status": "done", "progress_pct": 100,
                                     "stage_log_append": "✓ 完成"})
        assert r.json()["status"] == "done"
        assert "计算各叶子缺口" in r.json()["stage_log"]


@pytest.mark.asyncio
async def test_reverse_fill_writes_reverse_draft_fp(client_factory, db_session):
    """cost-fill 写入的 FP source=reverse_draft，能被 functions API 读出。"""
    _seed(db_session, pid="p-revfill-3")
    async with await client_factory() as client:
        r = await client.post(
            "/api/projects/p-revfill-3/functions/bulk",
            headers={**H, "Content-Type": "application/json"},
            json={"items": [{
                "subsystem": "结算", "l1_module": "资金", "l2_module": "查询",
                "name": "AI补全-账户明细查询", "category": "EQ",
                "complexity": "average", "det": 12, "ftr": 2,
                "ufp": 4, "us": 4, "modify_type": "add",
                "source": "reverse_draft",
                "description": "按反算缺口补全的功能点草稿",
            }], "replace": False},
        )
        assert r.status_code == 201
        r = await client.get("/api/projects/p-revfill-3/functions", headers=H)
        sources = {fp["source"] for fp in r.json()["data"]}
        assert "reverse_draft" in sources
        assert "manual" in sources  # replace=False 未覆盖用户已有 FP
