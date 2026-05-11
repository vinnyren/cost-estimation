"""/review round 5 adversarial fixes regression tests.

Covers:
  - F1 (services.params.validate_override_key): reject bare/unknown keys
  - F4 (UNIQUE(project_id, version) on fp_snapshots): duplicate fails
  - F6 (bulk_write pre-replace snapshot): create-then-replace is recoverable
  - G3 (parsed_text_path relative): stored path is relative + resolves OK
"""
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}
FIX = Path(__file__).parent.parent / "fixtures"


async def _make_project(c) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": "T", "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    return r.json()["data"]["id"]


# -------- F1: param override key validation --------

async def test_override_bare_cf_rejected(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        r = await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"cf": 42},  # 顶层 dict 单段键 — 必须拒
        )
        assert r.status_code == 422
        assert "INVALID_PARAM_KEY" in r.text


async def test_override_unknown_path_rejected(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        r = await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"evil.bogus.path": 1},
        )
        assert r.status_code == 422


async def test_override_real_leaf_accepted(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        r = await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"city_rate.北京.dev": 99999},
        )
        assert r.status_code == 200
        assert r.json()["data"]["city_rate"]["北京"]["dev"] == 99999


async def test_override_hours_per_pm_single_segment_leaf_ok(client_factory):
    """hours_per_pm 是真正的顶层标量 leaf，单段 key 应该允许。"""
    async with await client_factory() as client:
        pid = await _make_project(client)
        r = await client.patch(
            f"/api/projects/{pid}/params/override",
            headers={**H, "Content-Type": "application/json"},
            json={"hours_per_pm": 160},
        )
        assert r.status_code == 200
        assert r.json()["data"]["hours_per_pm"] == 160


async def test_patch_global_bare_dict_key_rejected(client_factory):
    async with await client_factory() as client:
        r = await client.patch(
            "/api/params/global",
            headers={**H, "Content-Type": "application/json"},
            json={"key": "productivity_dev", "value": 99},
        )
        assert r.status_code == 422


async def test_patch_global_unknown_key_rejected(client_factory):
    async with await client_factory() as client:
        r = await client.patch(
            "/api/params/global",
            headers={**H, "Content-Type": "application/json"},
            json={"key": "random_garbage_key", "value": 1},
        )
        assert r.status_code == 422


# -------- F4: UNIQUE(project_id, version) on fp_snapshots --------

async def test_duplicate_snapshot_version_rejected_at_db(client_factory, db_session):
    """直接走服务层 _snapshot 验证 UNIQUE 约束生效。"""
    async with await client_factory() as client:
        pid = await _make_project(client)
        import app.services.functions as fs
        # 写一个 FP 让 snapshot 不是 empty
        from app.db.models import FunctionPoint
        db_session.add(FunctionPoint(
            id="fp-test-1", project_id=pid, version=1,
            category="EI", complexity="low", ufp=3, us=3, source="manual",
        ))
        db_session.commit()
        fs._snapshot(db_session, pid, 1, reason="first")
        with pytest.raises(IntegrityError):
            fs._snapshot(db_session, pid, 1, reason="dup")
            db_session.commit()
        db_session.rollback()


# -------- F6: bulk_write pre-replace snapshot --------

async def test_create_then_bulk_replace_preserves_via_snapshot(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        # 通过单体 POST /functions 创建 FP（不会触发 bulk snapshot）
        r1 = await client.post(
            f"/api/projects/{pid}/functions",
            headers={**H, "Content-Type": "application/json"},
            json={"name": "single-fp", "category": "EI", "complexity": "low",
                  "ufp": 3, "us": 3, "source": "manual"},
        )
        assert r1.status_code == 201
        # 现在 bulk_write(replace=True) — 应当自动 pre-snapshot 之前的单体 FP
        await client.post(
            f"/api/projects/{pid}/functions/bulk",
            headers={**H, "Content-Type": "application/json"},
            json={
                "items": [{"name": "bulk-fp", "category": "EQ", "complexity": "average",
                            "ufp": 4, "us": 4, "source": "manual"}],
                "replace": True,
            },
        )
        # 查 snapshots
        snaps = (await client.get(
            f"/api/projects/{pid}/functions/snapshots", headers=H
        )).json()["data"]
        pre_replace = [s for s in snaps if s["reason"] == "pre_bulk_replace"]
        assert len(pre_replace) == 1, f"missing pre_bulk_replace snapshot: {snaps}"
        # 恢复到那个 version 应当带回 single-fp
        pre_v = pre_replace[0]["version"]
        await client.post(f"/api/projects/{pid}/functions/restore?version={pre_v}", headers=H)
        fps = (await client.get(f"/api/projects/{pid}/functions", headers=H)).json()["data"]
        names = [f["name"] for f in fps]
        assert "single-fp" in names


async def test_bulk_replace_on_empty_does_not_create_extra_snapshot(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client)
        await client.post(
            f"/api/projects/{pid}/functions/bulk",
            headers={**H, "Content-Type": "application/json"},
            json={
                "items": [{"name": "x", "category": "EI", "complexity": "low",
                            "ufp": 3, "us": 3, "source": "manual"}],
                "replace": True,
            },
        )
        snaps = (await client.get(
            f"/api/projects/{pid}/functions/snapshots", headers=H
        )).json()["data"]
        # 第一次 bulk 在空表上跑：只有 post-write 一道快照
        assert all(s["reason"] != "pre_bulk_replace" for s in snaps)


# -------- G3: parsed_text_path stored relative --------

async def test_upload_parsed_text_path_is_relative(client_factory, tmp_data_dir):
    async with await client_factory() as client:
        pid = await _make_project(client)
        with open(FIX / "sample.pdf", "rb") as f:
            r = await client.post(
                f"/api/projects/{pid}/uploads",
                headers=H,
                files={"file": ("doc.pdf", f, "application/pdf")},
            )
        assert r.status_code == 201
        parsed = r.json()["data"]["parsed_text_path"]
        # 不应当以 / 起头（绝对路径）
        assert not parsed.startswith("/"), f"parsed_text_path leaked absolute path: {parsed}"
        assert pid in parsed
