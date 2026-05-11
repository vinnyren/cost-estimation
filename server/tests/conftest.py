from typing import Any, Iterator

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


# ---------------------------------------------------------------------------
# v2.1 测试基础设施 — per-test ephemeral SQLite + dependency override
# ---------------------------------------------------------------------------


@pytest.fixture
def db_engine() -> Iterator[Any]:
    """v2.1 — 每 test 一个 in-memory SQLite engine。

    StaticPool 让 fixture 创建的多个 session（如果有）共享同一连接，
    所以建在内存里的表对所有 session 可见。check_same_thread=False
    让 FastAPI 的异步 endpoint 在不同 thread 上访问也行。

    yield 后 dispose — 内存表跟着 GC，零 disk 残留。
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from app.db.session import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Iterator[Any]:
    """每 test 一个 Session，绑到 db_engine。"""
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False,
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client_factory(db_session, monkeypatch):
    """工厂 fixture — 返回 async callable 用来构造 AsyncClient。

    用法（async test）::

        async def test_xxx(client_factory):
            async with await client_factory() as c:
                r = await c.get('/api/...')

    fixture 内部：注入 db_session 替代 FastAPI 的 get_db；按需 seed CSBMK；
    auth token 用 'test-secret-token-xyz'。
    """
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")

    async def _make(seed_csbmk: bool = True):
        from httpx import ASGITransport, AsyncClient

        from app.db.session import get_db
        from app.main import create_app
        from app.services import params as ps

        if seed_csbmk:
            try:
                # v2.1 T2 之后 seed_from_csbmk 接受 db 参数
                ps.seed_from_csbmk(db=db_session)  # type: ignore[call-arg]
            except TypeError:
                # T1 阶段（T2 未实施）seed_from_csbmk 还是无参数签名
                ps.seed_from_csbmk()
            db_session.commit()

        app = create_app()
        app.dependency_overrides[get_db] = lambda: db_session
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    return _make
