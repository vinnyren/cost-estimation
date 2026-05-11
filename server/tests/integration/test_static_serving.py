"""集成：FastAPI 在生产期托管 web/dist。

覆盖 spec §9.5 的静态托管 + SPA fallback 行为：
- 根路径返回 index.html
- /assets/* 返回前端静态资源
- 任意未知路径 SPA fallback → index.html
- /api/* 与 /health 不被 SPA fallback 吞掉
"""
from __future__ import annotations

import pytest


@pytest.fixture
def web_dist_dir(tmp_path, monkeypatch):
    """构造一个临时 web/dist 目录并通过环境变量推给 client_factory。

    SPA shell + assets 是浏览器自发请求（无 X-Auth-Token header），
    因此 token 中间件对非 /api/ GET 请求免认证；token 仍保护所有 /api/* 路由。
    create_app 内部读 `fresh.web_dist_dir = Settings().web_dist_dir`，
    所以 setenv 之后调用 client_factory 触发的 create_app() 会读到新值。
    """
    dist = tmp_path / "web_dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<!doctype html><html><body>web app</body></html>", encoding="utf-8",
    )
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    monkeypatch.setenv("COST_WEB_DIST_DIR", str(dist))
    return dist


async def test_serves_index_html(client_factory, web_dist_dir):
    async with await client_factory() as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "web app" in resp.text


async def test_serves_static_asset(client_factory, web_dist_dir):
    async with await client_factory() as client:
        resp = await client.get("/assets/app.js")
        assert resp.status_code == 200
        assert "console.log" in resp.text


async def test_spa_fallback_for_unknown_route(client_factory, web_dist_dir):
    async with await client_factory() as client:
        resp = await client.get("/projects/1/functions")
        assert resp.status_code == 200
        assert "web app" in resp.text


async def test_api_routes_unaffected(client_factory, web_dist_dir):
    async with await client_factory() as client:
        resp = await client.get(
            "/api/projects",
            headers={"X-Auth-Token": "test-secret-token-xyz"},
        )
        # 200=空列表 / 4xx=已实现错误；都不应返回 SPA shell HTML
        assert "web app" not in resp.text
