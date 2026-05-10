import pytest


@pytest.fixture
def app():
    # Lazy import: 仅 integration tests 需要 FastAPI app；
    # unit tests 不应触发 SQLAlchemy/FastAPI 加载（mutmut 在 fork 子进程跑时
    # 全局 SQLAlchemy state 易导致 SIGSEGV）。
    from app.main import create_app
    return create_app()


@pytest.fixture
async def client(app):
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
