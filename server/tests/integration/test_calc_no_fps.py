"""Integration: forward 计算在项目无功能点时必须返回 422 + NO_FUNCTION_POINTS。

回归 v1.1 polish 发现的 MEDIUM bug：旧版 _resolve_items 在 forward 模式下
DB 拉取 functions 为空时静默返回 [], 导致 calculate_forward 输出 scale_us=0
cost ≈ other_cost。前端看不到错误，以为系统坏了。

修法：services.calc._resolve_items 在 forward 模式下若 payload.items 为空
且 DB 也无 FP 行，抛 ValueError("NO_FUNCTION_POINTS: ...")。API 层将
非 PROJECT_NOT_FOUND 的 ValueError 映射为 422。
"""
from __future__ import annotations

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def _make_empty_project(c) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": "no-fps-test",
        "project_type": "dev_only",
        "phase": "bidding",
        "city": "北京",
        "industry": "电子政务",
        "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    return r.json()["data"]["id"]


async def test_forward_no_function_points_returns_422(client_factory):
    """forward 模式下项目无 FP 且 payload 也不带 items，server 应返回 422
    且 error.code == NO_FUNCTION_POINTS。"""
    async with await client_factory() as c:
        pid = await _make_empty_project(c)
        r = await c.post(
            "/api/calc/forward",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": pid, "dev_factor": 1.0, "include_dev": True},
        )
        assert r.status_code == 422, r.text
        body = r.json()
        code = body.get("detail", {}).get("error", {}).get("code", "")
        assert code == "NO_FUNCTION_POINTS", body


async def test_forward_with_payload_items_still_works(client_factory):
    """无 DB FP 但 payload 显式给 items 时应正常计算（不触发 NO_FUNCTION_POINTS）。"""
    async with await client_factory() as c:
        pid = await _make_empty_project(c)
        r = await c.post(
            "/api/calc/forward",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": pid, "items": [{"us": 100}],
                  "dev_factor": 1.0, "include_dev": True},
        )
        assert r.status_code == 200, r.text
        assert r.json()["data"]["scale_us"] == 100


async def test_forward_unknown_project_still_404(client_factory):
    """PROJECT_NOT_FOUND 仍应返回 404（不被 NO_FUNCTION_POINTS 路径误捕）。"""
    async with await client_factory() as c:
        r = await c.post(
            "/api/calc/forward",
            headers={**H, "Content-Type": "application/json"},
            json={"project_id": "prj-does-not-exist",
                  "items": [{"us": 100}], "include_dev": True},
        )
        assert r.status_code == 404, r.text
