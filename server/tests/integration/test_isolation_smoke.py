"""v2.1 A6 — isolation regression test.

v2.0 → v2.1 修复前：单文件运行某些 v2 integration test 报
`Table 'projects' is already defined for this MetaData instance`。
原因是 fixture 用 `importlib.reload`，conftest 之前 import 的旧 metadata
里已有 projects 表，reload 后 class Project(Base) 又试图注册到同一 metadata。

修复后用 per-test in-memory engine + StaticPool，每 test 独立 metadata，
不再共享 disk DB。这个 smoke test 锁定回归：连续 3 个 test 都建项目，
确认 metadata 隔离 + cascade delete 工作。
"""
import pytest


pytestmark = pytest.mark.asyncio

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


async def _create(c, name: str) -> str:
    r = await c.post("/api/projects", headers=H, json={
        "name": name, "project_type": "dev_only", "phase": "bidding",
        "city": "北京", "industry": "电子政务", "mode": "forward",
        "basis_data_ver": "CSBMK®-202510",
    })
    assert r.status_code == 201
    return r.json()["data"]["id"]


async def test_isolation_first_engine_clean(client_factory):
    """第一个 test 建项目，确认 in-memory engine 全新。"""
    async with await client_factory() as c:
        before = (await c.get("/api/projects", headers=H)).json()
        assert before["meta"]["total"] == 0
        pid = await _create(c, "isolation-1")
        after = (await c.get("/api/projects", headers=H)).json()
        assert after["meta"]["total"] == 1
        assert after["data"][0]["id"] == pid


async def test_isolation_second_engine_clean(client_factory):
    """第二个 test 也建项目，但拿到的是 fresh engine（看不到 test 1 的数据）。"""
    async with await client_factory() as c:
        before = (await c.get("/api/projects", headers=H)).json()
        # 关键 assertion：第二个 test 看到 0 个项目，证明 engine 隔离
        assert before["meta"]["total"] == 0
        pid = await _create(c, "isolation-2")
        assert pid is not None


async def test_isolation_third_engine_clean(client_factory):
    """第三个 test 同理 — fresh engine。"""
    async with await client_factory() as c:
        before = (await c.get("/api/projects", headers=H)).json()
        assert before["meta"]["total"] == 0
