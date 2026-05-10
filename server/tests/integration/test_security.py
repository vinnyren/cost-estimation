import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app_with_token(monkeypatch):
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")
    return create_app()


@pytest.fixture
async def secured_client(app_with_token):
    transport = ASGITransport(app=app_with_token)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_does_not_require_token(secured_client):
    r = await secured_client.get("/health")
    assert r.status_code == 200


async def test_api_without_token_returns_401(secured_client):
    r = await secured_client.get("/api/projects")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


async def test_api_with_valid_token_via_header_passes(secured_client):
    r = await secured_client.get(
        "/api/projects",
        headers={"X-Auth-Token": "test-secret-token-xyz"},
    )
    assert r.status_code != 401  # 路由可能未实现，但不应是 401


async def test_api_with_valid_token_via_query_passes(secured_client):
    r = await secured_client.get("/api/projects?t=test-secret-token-xyz")
    assert r.status_code != 401


async def test_post_with_evil_origin_blocked(secured_client):
    r = await secured_client.post(
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


async def test_post_with_localhost_origin_passes(secured_client):
    r = await secured_client.post(
        "/api/projects",
        headers={
            "X-Auth-Token": "test-secret-token-xyz",
            "Origin": "http://127.0.0.1:8788",
            "Content-Type": "application/json",
        },
        json={"name": "x"},
    )
    assert r.status_code != 403


async def test_get_without_origin_passes(secured_client):
    r = await secured_client.get(
        "/api/projects",
        headers={"X-Auth-Token": "test-secret-token-xyz"},
    )
    assert r.status_code != 403
