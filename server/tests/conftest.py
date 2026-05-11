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

    PRAGMA foreign_keys=ON — 让 ON DELETE CASCADE 真的工作；
    SQLite 默认 FK off，production engine 通过 session.py 的 event
    listener 启用，in-memory 测试 engine 这里复刻同样的行为。

    yield 后 dispose — 内存表跟着 GC，零 disk 残留。
    """
    from sqlalchemy import create_engine, event
    from sqlalchemy.pool import StaticPool

    # 必须先 import models 让 ORM 类注册到 Base.metadata；
    # 单文件隔离运行时，没有上游导入触发 model 模块加载，
    # `create_all` 会建一张空 schema。
    import app.db.models  # noqa: F401
    from app.db.session import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(conn, _):
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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
def client_factory(db_engine, db_session, monkeypatch):
    """工厂 fixture — 返回 async callable 用来构造 AsyncClient。

    用法（async test）::

        async def test_xxx(client_factory):
            async with await client_factory() as c:
                r = await c.get('/api/...')

    fixture 内部：
      1) monkeypatch app.db.session.SessionLocal 绑到 in-memory engine —
         覆盖那些不走 get_db 依赖、直接 `SessionLocal()` 的代码路径
         （比如 audit middleware）。
      2) 注入 db_session 替代 FastAPI 的 get_db。
      3) 按需 seed CSBMK；auth token 用 'test-secret-token-xyz'。
    """
    monkeypatch.setenv("COST_AUTH_TOKEN", "test-secret-token-xyz")

    # 把 module-level SessionLocal 重绑到测试 in-memory engine。
    # 直接拿 SessionLocal() 的代码（如 app/middleware/audit.py）会拿到
    # 绑到 in-memory engine 的 session，写入对 test 的 db_session 也可见
    # （StaticPool 共享同一连接）。
    # 注意：用 `from ..db.session import SessionLocal` 直接 import 的模块
    # 会保留旧绑定，所以也要 patch 这些模块的 SessionLocal 引用。
    from sqlalchemy.orm import sessionmaker

    import app.db.session as session_module

    test_session_local = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False,
    )
    monkeypatch.setattr(session_module, "SessionLocal", test_session_local)
    # 已用 `from ..db.session import SessionLocal` 的模块需要单独 patch
    try:
        import app.middleware.audit as audit_module
        monkeypatch.setattr(audit_module, "SessionLocal", test_session_local)
    except ImportError:
        pass

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
