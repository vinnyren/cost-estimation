"""v2.8 — 旧 modify_type 值（new/modify）的向后兼容。"""
import pytest
from app.schemas.functions import FunctionPointBase


def test_legacy_new_normalized_to_add():
    fp = FunctionPointBase(name="x", category="EI", complexity="low",
                           modify_type="new", ufp=3, us=3)
    assert fp.modify_type == "add"


def test_legacy_modify_normalized_to_change():
    fp = FunctionPointBase(name="x", category="EI", complexity="low",
                           modify_type="modify", ufp=3, us=3)
    assert fp.modify_type == "change"


def test_current_values_pass_through():
    for mt in ("add", "change", "delete", "convert"):
        fp = FunctionPointBase(name="x", category="EI", complexity="low",
                               modify_type=mt, ufp=3, us=3)
        assert fp.modify_type == mt


@pytest.mark.asyncio
async def test_import_v2_7_bundle_with_legacy_modify_type(client_factory, db_session):
    """v2.7 导出的 bundle 含 modify_type='new'，导入应成功并归一化。"""
    H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788",
         "Content-Type": "application/json"}
    bundle = {
        "version": "2.7", "exported_at": "2026-01-01T00:00:00Z",
        "projects": [{
            "name": "legacy import", "project_type": "dev_only", "phase": "bidding",
            "city": "北京", "industry": "电子政务", "mode": "forward",
            "other_cost": 0, "include_ops": False, "alpha_dev": 1.0,
            "measurement_method": "nesma_estimated", "basis_data_ver": "CSBMK®-202510",
            "param_overrides": [],
            "function_points": [{
                "name": "登录", "category": "EI", "complexity": "low",
                "ufp": 3, "us": 3, "modify_type": "new",
            }],
        }],
    }
    async with await client_factory() as client:
        r = await client.post("/api/projects/import", headers=H, json=bundle)
        assert r.status_code in (200, 201)
