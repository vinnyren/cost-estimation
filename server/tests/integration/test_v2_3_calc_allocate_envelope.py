"""v2.3 — POST /api/calc/allocate 返回 envelope {items, validation}."""
import pytest
from app.db.models import Project

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def _seed(db, pid="p-alloc-env"):
    p = Project(id=pid, name="alloc env",
                project_type="dev_only", phase="bidding",
                city="北京", industry="电子政务",
                mode="reverse", basis_data_ver="CSBMK-202510")
    db.add(p)
    db.commit()
    return p


@pytest.mark.asyncio
async def test_allocate_returns_envelope(client_factory, db_session):
    _seed(db_session)
    async with await client_factory() as client:
        r = await client.post(
            "/api/calc/allocate",
            headers={**H, "Content-Type": "application/json"},
            json={
                "project_id": "p-alloc-env",
                "target_us": 275.0,
                "cf": 1.21,
                "drafts": [
                    {"name": "前端", "weight": 1.0},
                    {"name": "后端", "weight": 1.5},
                ],
            },
        )
        assert r.status_code == 200
        body = r.json()
        # 现有 api 包了一层 {ok, data}; data 现在是 envelope
        assert body.get("ok") is True
        data = body["data"]
        assert "items" in data
        assert "validation" in data
        assert len(data["items"]) == 2
        assert isinstance(data["validation"]["error_pct"], float)
