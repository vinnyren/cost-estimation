"""Auth + Origin guard tests.

Migrated from local create_app() fixture to conftest.client_factory in v2.1 A5:
the previous fixture used the production engine, which only worked because
earlier tests' importlib.reload polluted app.db.session.engine into a fresh
tmp DB. After v2.1 migrated those tests to in-memory engines, this file
needed its own ephemeral DB — provided by client_factory.
"""


async def test_health_does_not_require_token(client_factory):
    async with await client_factory() as c:
        r = await c.get("/health")
        assert r.status_code == 200


async def test_api_without_token_returns_401(client_factory):
    async with await client_factory() as c:
        r = await c.get("/api/projects")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHORIZED"


async def test_api_with_valid_token_via_header_passes(client_factory):
    async with await client_factory() as c:
        r = await c.get(
            "/api/projects",
            headers={"X-Auth-Token": "test-secret-token-xyz"},
        )
        assert r.status_code != 401  # 路由可能未实现，但不应是 401


async def test_api_with_valid_token_via_query_passes(client_factory):
    async with await client_factory() as c:
        r = await c.get("/api/projects?t=test-secret-token-xyz")
        assert r.status_code != 401


async def test_post_with_evil_origin_blocked(client_factory):
    async with await client_factory() as c:
        r = await c.post(
            "/api/projects",
            headers={
                "X-Auth-Token": "test-secret-token-xyz",
                "Origin": "https://evil.com",
                "Content-Type": "application/json",
            },
            json={"name": "x"},
        )
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "FORBIDDEN_ORIGIN"


async def test_post_with_localhost_origin_passes(client_factory):
    async with await client_factory() as c:
        r = await c.post(
            "/api/projects",
            headers={
                "X-Auth-Token": "test-secret-token-xyz",
                "Origin": "http://127.0.0.1:8788",
                "Content-Type": "application/json",
            },
            json={"name": "x"},
        )
        assert r.status_code != 403


async def test_get_without_origin_passes(client_factory):
    async with await client_factory() as c:
        r = await c.get(
            "/api/projects",
            headers={"X-Auth-Token": "test-secret-token-xyz"},
        )
        assert r.status_code != 403
