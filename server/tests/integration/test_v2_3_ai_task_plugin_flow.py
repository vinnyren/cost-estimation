"""v2.3 — plugin HTTP 上报流程模拟测试。

模拟 /cost <project_id> 和 /cost-allocate <project_id> 执行时会发出的
HTTP 调用序列，验证 AiTask record 状态机一致。

Plugin 是 markdown 不能直接 exec，但 HTTP 序列可以完整复现。
"""
import pytest
from app.db.models import Project

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def _seed_project(db, pid="p-plugin-flow"):
    p = Project(
        id=pid, name="plugin flow test",
        project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务",
        mode="forward", basis_data_ver="CSBMK-202510",
    )
    db.add(p)
    db.commit()
    return p


@pytest.mark.asyncio
async def test_extract_plugin_6_step_flow(client_factory, db_session):
    """模拟 /cost extract 的 6 次 HTTP 调用。"""
    _seed_project(db_session)
    async with await client_factory() as client:
        # T0: 创建 task
        r = await client.post("/api/ai-tasks", headers=H,
                               json={"project_id": "p-plugin-flow", "kind": "extract"})
        assert r.status_code == 201
        task_id = r.json()["id"]

        # T1-T4: 4 次 progress PATCH
        for pct, log in [
            (10, "✓ 文档解析"),
            (30, "✓ 章节切分"),
            (55, "✓ EI/EO/EQ/ILF/EIF 类别归类"),
            (85, "✓ 写入 FP 表"),
        ]:
            body = {"status": "running", "progress_pct": pct, "stage_log_append": log}
            r = await client.patch(f"/api/ai-tasks/{task_id}", headers=H, json=body)
            assert r.status_code == 200
            assert r.json()["progress_pct"] == pct

        # T5: 完成
        r = await client.patch(
            f"/api/ai-tasks/{task_id}",
            headers=H,
            json={"status": "done", "progress_pct": 100, "stage_log_append": "✓ 完成",
                  "output_json": '{"task_id":"p-plugin-flow"}'},
        )
        assert r.status_code == 200
        final = r.json()
        assert final["status"] == "done"
        assert final["progress_pct"] == 100
        # 所有 stage_log 段都累加到一起
        assert "文档解析" in final["stage_log"]
        assert "章节切分" in final["stage_log"]
        assert "类别归类" in final["stage_log"]
        assert "写入 FP 表" in final["stage_log"]
        assert "完成" in final["stage_log"]
        assert final["output_json"] == '{"task_id":"p-plugin-flow"}'


@pytest.mark.asyncio
async def test_allocate_plugin_4_step_flow(client_factory, db_session):
    """模拟 /cost-allocate 的 4 次 HTTP 调用。"""
    _seed_project(db_session, pid="p-plugin-flow-2")
    async with await client_factory() as client:
        r = await client.post("/api/ai-tasks", headers=H,
                               json={"project_id": "p-plugin-flow-2", "kind": "allocate"})
        task_id = r.json()["id"]
        for pct, log in [(20, "✓ 加载项目反向结果"), (70, "✓ AI 推荐权重")]:
            r = await client.patch(f"/api/ai-tasks/{task_id}", headers=H,
                                   json={"status": "running", "progress_pct": pct, "stage_log_append": log})
            assert r.status_code == 200

        r = await client.patch(
            f"/api/ai-tasks/{task_id}",
            headers=H,
            json={"status": "done", "progress_pct": 100, "stage_log_append": "✓ 完成"},
        )
        assert r.json()["status"] == "done"
        assert "AI 推荐权重" in r.json()["stage_log"]
        assert "加载项目反向结果" in r.json()["stage_log"]


@pytest.mark.asyncio
async def test_failure_path_marks_task_failed(client_factory, db_session):
    """模拟 plugin 中途失败的兜底 PATCH。"""
    _seed_project(db_session, pid="p-plugin-flow-3")
    async with await client_factory() as client:
        r = await client.post("/api/ai-tasks", headers=H,
                               json={"project_id": "p-plugin-flow-3", "kind": "extract"})
        task_id = r.json()["id"]
        # T1 OK
        await client.patch(f"/api/ai-tasks/{task_id}", headers=H,
                           json={"status": "running", "progress_pct": 10, "stage_log_append": "✓ 文档解析"})
        # 中断 — failed
        r = await client.patch(f"/api/ai-tasks/{task_id}", headers=H,
                               json={"status": "failed", "error_message": "提取流程中断"})
        assert r.status_code == 200
        assert r.json()["status"] == "failed"
        assert r.json()["error_message"] == "提取流程中断"
