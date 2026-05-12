"""v2.5 — POST /api/ai-tasks/{id}/start + /stop endpoints."""
import pytest
from unittest.mock import patch
from app.db.models import Project

H = {"X-Auth-Token": "test-secret-token-xyz"}


def _seed(db, pid="p-start"):
    p = Project(
        id=pid, name="start stop test",
        project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务",
        mode="forward", basis_data_ver="CSBMK-202510",
    )
    db.add(p)
    db.commit()
    return p


@pytest.mark.asyncio
async def test_start_task_spawns_claude_when_available(client_factory, db_session):
    _seed(db_session)
    async with await client_factory(seed_csbmk=False) as client:
        r = await client.post("/api/ai-tasks", json={"project_id": "p-start", "kind": "extract"}, headers=H)
        assert r.status_code == 201
        task_id = r.json()["id"]
        with patch("app.api.ai_tasks.svc.spawn_claude_extract", return_value=54321):
            r = await client.post(f"/api/ai-tasks/{task_id}/start", headers=H)
        assert r.status_code == 200
        assert r.json()["pid"] == 54321


@pytest.mark.asyncio
async def test_start_task_returns_500_when_claude_missing(client_factory, db_session):
    _seed(db_session, pid="p-start-2")
    async with await client_factory(seed_csbmk=False) as client:
        r = await client.post("/api/ai-tasks", json={"project_id": "p-start-2", "kind": "extract"}, headers=H)
        assert r.status_code == 201
        task_id = r.json()["id"]
        with patch("app.api.ai_tasks.svc.spawn_claude_extract", return_value=None):
            r = await client.post(f"/api/ai-tasks/{task_id}/start", headers=H)
        assert r.status_code == 500
        assert "claude" in r.json()["detail"]["error"]["code"].lower()


@pytest.mark.asyncio
async def test_stop_task_calls_kill(client_factory, db_session):
    _seed(db_session, pid="p-stop")
    async with await client_factory(seed_csbmk=False) as client:
        r = await client.post("/api/ai-tasks", json={"project_id": "p-stop", "kind": "extract"}, headers=H)
        assert r.status_code == 201
        task_id = r.json()["id"]
        with patch("app.api.ai_tasks.svc.spawn_claude_extract", return_value=11111):
            await client.post(f"/api/ai-tasks/{task_id}/start", headers=H)
        with patch("app.api.ai_tasks.svc.stop_claude_subprocess", return_value=True) as mock_stop:
            r = await client.post(f"/api/ai-tasks/{task_id}/stop", headers=H)
        assert r.status_code == 200
        assert r.json()["stopped"] is True
        mock_stop.assert_called_once_with(11111)


@pytest.mark.asyncio
async def test_create_task_dedup_within_30s_window(client_factory, db_session):
    """/qa: UI 和 plugin 同时 POST /api/ai-tasks 同 (project_id, kind) 应复用同一行。"""
    _seed(db_session, pid="p-dedup")
    async with await client_factory(seed_csbmk=False) as client:
        r1 = await client.post(
            "/api/ai-tasks",
            json={"project_id": "p-dedup", "kind": "extract"},
            headers=H,
        )
        assert r1.status_code == 201
        task_id_1 = r1.json()["id"]

        # 模拟 plugin POST 同 (project_id, kind) 应复用
        r2 = await client.post(
            "/api/ai-tasks",
            json={"project_id": "p-dedup", "kind": "extract"},
            headers=H,
        )
        assert r2.status_code == 201
        task_id_2 = r2.json()["id"]
        assert task_id_1 == task_id_2, "30s 内同 (project_id, kind) 应复用同一 task"


@pytest.mark.asyncio
async def test_stop_task_refuses_to_overwrite_done_status(client_factory, db_session):
    """/review F2: /stop 在 task 已 done 时应返回 409，不能把 done 改写为 failed。"""
    _seed(db_session, pid="p-stop-done")
    async with await client_factory(seed_csbmk=False) as client:
        r = await client.post(
            "/api/ai-tasks",
            json={"project_id": "p-stop-done", "kind": "extract"},
            headers=H,
        )
        task_id = r.json()["id"]
        # 模拟 plugin 已完成：PATCH 把 task 推到 done
        with patch("app.api.ai_tasks.svc.spawn_claude_extract", return_value=22222):
            await client.post(f"/api/ai-tasks/{task_id}/start", headers=H)
        r = await client.patch(
            f"/api/ai-tasks/{task_id}",
            json={"status": "done", "progress_pct": 100, "stage_log_append": "✓ 完成"},
            headers=H,
        )
        assert r.status_code == 200

        # 用户在 done 之后再点 "停止" — 应该被拒
        r = await client.post(f"/api/ai-tasks/{task_id}/stop", headers=H)
        assert r.status_code == 409
        assert r.json()["detail"]["error"]["code"] == "TASK_ALREADY_DONE"

        # 验证 task 状态没被改回 failed
        r = await client.get(f"/api/ai-tasks/{task_id}", headers=H)
        assert r.json()["status"] == "done"
