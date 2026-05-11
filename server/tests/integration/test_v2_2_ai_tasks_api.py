"""v2.2 — /api/ai-tasks 端到端。"""
from app.db.models import Project

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def _seed_project(db, pid="p-ai-api"):
    p = Project(
        id=pid, name="api test",
        project_type="dev_only", phase="bidding",
        city="北京", industry="电子政务",
        mode="forward", basis_data_ver="CSBMK-202510",
    )
    db.add(p)
    db.commit()
    return p


async def test_ai_task_crud_flow(client_factory, db_session):
    _seed_project(db_session)
    async with await client_factory() as client:
        # create
        r = await client.post(
            "/api/ai-tasks",
            headers=H,
            json={"project_id": "p-ai-api", "kind": "extract"},
        )
        assert r.status_code == 201
        body = r.json()
        task_id = body["id"]
        assert body["status"] == "queued"
        assert body["progress_pct"] == 0.0

        # patch progress
        r = await client.patch(
            f"/api/ai-tasks/{task_id}",
            headers=H,
            json={"status": "running", "progress_pct": 48.0, "stage_log_append": "✓ 解析完成"},
        )
        assert r.status_code == 200
        assert r.json()["progress_pct"] == 48.0
        assert "解析完成" in r.json()["stage_log"]

        # list
        r = await client.get(
            "/api/ai-tasks?project_id=p-ai-api",
            headers={"X-Auth-Token": "test-secret-token-xyz"},
        )
        assert r.status_code == 200
        assert len(r.json()) == 1

        # read one
        r = await client.get(
            f"/api/ai-tasks/{task_id}",
            headers={"X-Auth-Token": "test-secret-token-xyz"},
        )
        assert r.status_code == 200
        assert r.json()["id"] == task_id

        # 404 on unknown
        r = await client.patch(
            "/api/ai-tasks/non-existent",
            headers=H,
            json={"status": "done"},
        )
        assert r.status_code == 404
