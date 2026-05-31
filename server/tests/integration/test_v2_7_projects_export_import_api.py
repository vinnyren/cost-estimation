"""Integration tests for POST /api/projects/export & /import (v2.7).

导出选定项目为 JSON bundle；导入同格式 bundle 总是新建项目。
round-trip 必须完整还原项目元数据 + FP + 参数 override，且生成新 id。
"""

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}
HJ = {**H, "Content-Type": "application/json"}


async def _make_project(c, name: str) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": name, "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510", "client": "甲方A",
    })
    return r.json()["data"]["id"]


async def test_export_returns_bundle_with_core_fields(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client, "导出项目")
        r = await client.post("/api/projects/export", headers=HJ,
                               json={"ids": [pid]})
        assert r.status_code == 200
        bundle = r.json()["data"]
        assert bundle["version"] == "2.7"
        assert "exported_at" in bundle
        assert len(bundle["projects"]) == 1
        proj = bundle["projects"][0]
        assert proj["name"] == "导出项目"
        assert proj["client"] == "甲方A"
        assert "id" not in proj
        assert "function_points" in proj
        assert "param_overrides" in proj


async def test_export_skips_unknown_ids(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client, "存在的项目")
        r = await client.post("/api/projects/export", headers=HJ,
                               json={"ids": [pid, "no-such-id"]})
        assert r.status_code == 200
        assert len(r.json()["data"]["projects"]) == 1


async def test_export_all_unknown_ids_returns_empty(client_factory):
    async with await client_factory() as client:
        r = await client.post("/api/projects/export", headers=HJ,
                               json={"ids": ["x", "y"]})
        assert r.status_code == 200
        assert r.json()["data"]["projects"] == []


async def test_import_creates_new_projects_round_trip(client_factory):
    async with await client_factory() as client:
        pid = await _make_project(client, "原始项目")
        await client.post(f"/api/projects/{pid}/functions", headers=HJ,
                          json={"name": "fp1", "category": "EI",
                                "complexity": "low", "ufp": 3, "us": 3,
                                "source": "manual"})
        bundle = (await client.post("/api/projects/export", headers=HJ,
                                    json={"ids": [pid]})).json()["data"]
        r = await client.post("/api/projects/import", headers=HJ, json=bundle)
        assert r.status_code == 200
        result = r.json()["data"]
        assert result["imported"] == 1
        new_id = result["project_ids"][0]
        assert new_id != pid
        new = (await client.get(f"/api/projects/{new_id}", headers=H)).json()["data"]
        assert new["name"] == "原始项目"
        assert new["client"] == "甲方A"
        fps = (await client.get(f"/api/projects/{new_id}/functions",
                                headers=H)).json()["data"]
        assert len(fps) == 1
        assert fps[0]["name"] == "fp1"


async def test_import_rejects_malformed_bundle(client_factory):
    async with await client_factory() as client:
        r = await client.post("/api/projects/import", headers=HJ,
                               json={"version": "2.7"})  # 缺 projects
        assert r.status_code == 400


async def test_import_rejects_project_missing_required_field(client_factory):
    async with await client_factory() as client:
        bad = {"version": "2.7", "exported_at": "2026-05-18T00:00:00Z",
               "projects": [{"name": "缺字段"}]}  # 缺 project_type 等
        r = await client.post("/api/projects/import", headers=HJ, json=bad)
        assert r.status_code == 400


# ── H1: bundle 规模上限 ────────────────────────────────────────────────────

_MIN_PROJECT = {
    "name": "x",
    "project_type": "dev_only",
    "phase": "bidding",
    "city": "北京",
    "industry": "电子政务",
    "mode": "forward",
    "basis_data_ver": "CSBMK®-202510",
}


async def test_import_rejects_bundle_with_201_projects(client_factory):
    """H1: projects 超过 200 条时 POST /api/projects/import 应返回 400。"""
    async with await client_factory() as client:
        big_bundle = {
            "version": "2.7",
            "exported_at": "2026-05-18T00:00:00Z",
            "projects": [_MIN_PROJECT.copy() for _ in range(201)],
        }
        r = await client.post("/api/projects/import", headers=HJ, json=big_bundle)
        assert r.status_code == 400


# ── H2: claude_draft 归一化 ───────────────────────────────────────────────

async def test_import_normalizes_claude_draft_source_to_ai_extracted(client_factory):
    """H2: 导出的 claude_draft FP 在导入后 source 应被归一化为 ai_extracted。"""
    async with await client_factory() as client:
        pid = await _make_project(client, "含草稿FP的项目")
        # 直接用 bulk 写入一个 claude_draft FP（或先创建后通过 bundle 注入）
        # 通过 bundle 注入：构造 bundle 使 FP source = claude_draft
        bundle = {
            "version": "2.7",
            "exported_at": "2026-05-18T00:00:00Z",
            "projects": [{
                **_MIN_PROJECT,
                "name": "含草稿FP的项目",
                "client": None,
                "evaluator": None,
                "target_cost": None,
                "other_cost": 0,
                "include_ops": False,
                "alpha_dev": 1.0,
                "measurement_method": "nesma_estimated",
                "factors_dev": None,
                "factors_ops": None,
                "param_overrides": [],
                "function_points": [
                    {
                        "name": "草稿fp",
                        "category": "EI",
                        "complexity": "low",
                        "ufp": 3,
                        "us": 3,
                        "source": "claude_draft",
                        "subsystem": None,
                        "l1_module": None,
                        "l2_module": None,
                        "description": None,
                        "fp_kind": "dev",
                        "reuse_level": "low",
                        "modify_type": "add",
                        "locked": False,
                        "notes": None,
                        "ord": 0,
                    }
                ],
            }],
        }
        r = await client.post("/api/projects/import", headers=HJ, json=bundle)
        assert r.status_code == 200
        new_id = r.json()["data"]["project_ids"][0]
        fps = (await client.get(f"/api/projects/{new_id}/functions",
                                headers=H)).json()["data"]
        assert len(fps) == 1
        assert fps[0]["source"] == "ai_extracted", (
            f"Expected source='ai_extracted', got {fps[0]['source']!r}"
        )
