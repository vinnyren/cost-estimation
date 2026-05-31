import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.health import router as health_router
from .api.projects import router as projects_router
from .api.params import router as params_router
from .api.calc import router as calc_router
from .api.uploads import router as uploads_router
from .api.functions import router as functions_router
from .api.reports import router as reports_router
from .api.snapshots import router as snapshots_router
from .api.audit import router as audit_router, global_router as audit_global_router
from .api.ai_tasks import router as ai_tasks_router
from .config import Settings, settings
from .deps import auth_middleware, origin_middleware
from .middleware.audit import AuditMiddleware


def _mount_web_dist(app: FastAPI, dist_path: str) -> None:
    """生产期挂载 web/dist 静态资源 + SPA fallback（spec §9.5）。

    - /assets/* → web/dist/assets/*（StaticFiles）
    - /          → web/dist/index.html（SPA shell）
    - /{spa_path} → web/dist/index.html（除 api/* 与 health 抛 404）

    必须在所有 API 路由 include_router 之后调用，否则 SPA fallback
    捕获通配符路径会吞掉真实 API 路由。
    """
    dist = Path(dist_path)
    if not dist.exists():
        return
    assets = dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    index = dist / "index.html"

    @app.get("/", include_in_schema=False)
    async def _root() -> FileResponse:
        return FileResponse(str(index))

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def _spa_fallback(spa_path: str) -> FileResponse:
        # 不能吞掉 api/* 与 health（已被前面的路由处理；防御性 404）
        if spa_path.startswith("api/") or spa_path == "health":
            raise HTTPException(status_code=404)
        return FileResponse(str(index))


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """FastAPI lifespan: 启动时建表 + seed CSBMK 默认参数；关闭时无显式清理。

    替代已弃用的 @app.on_event("startup")（FastAPI 0.93+ 提示迁移到
    lifespan context manager，统一启动/关闭语义）。
    """
    from .db.session import Base, engine
    from .services.params import seed_from_csbmk
    Base.metadata.create_all(bind=engine)
    seed_from_csbmk()
    yield
    # 关闭逻辑（目前无需）— SQLAlchemy engine 由进程退出时回收。


def create_app() -> FastAPI:
    fresh = Settings()
    settings.auth_token = fresh.auth_token
    if not settings.auth_token:
        settings.auth_token = secrets.token_urlsafe(32)
    # 生产期静态托管目录从环境同步（reload 友好）
    settings.web_dist_dir = fresh.web_dist_dir

    # 生产期（挂载 web/dist）关闭 FastAPI 内置 /docs /redoc /openapi.json —
    # 这些路由在 deps.auth_middleware 里命中「GET 且 非 /api/」分支被放行，
    # 任何能访问 loopback 的进程都能拉到完整 API 表面，作为 defense-in-depth
    # 在产品形态下关掉。开发模式（无 web_dist_dir）保留以便联调（ISSUE-008）。
    docs_kwargs: dict[str, str | None] = (
        {"docs_url": None, "redoc_url": None, "openapi_url": None}
        if fresh.web_dist_dir
        else {}
    )
    app = FastAPI(
        title="软件造价制作系统", version="2.9.0", lifespan=_lifespan,
        **docs_kwargs,  # type: ignore[arg-type]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"http://127.0.0.1:{settings.bind_port}",
                        f"http://localhost:{settings.bind_port}"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["X-Auth-Token", "Content-Type", "X-Requested-With"],
    )
    app.middleware("http")(origin_middleware)
    app.middleware("http")(auth_middleware)
    # AuditMiddleware 注册顺序：放在 auth/origin 之后（即在最外层、最后注册）。
    # Starlette 的执行顺序是「后注册先处理」，所以 audit 会在 auth/origin 之前
    # 拿到 request。但 audit 仅在 response 阶段写库，且对 2xx 之外的响应短路，
    # 因此即使未通过 auth 的请求也不会污染 audit_log。
    app.add_middleware(AuditMiddleware)

    app.include_router(health_router)
    app.include_router(projects_router)
    app.include_router(params_router)
    app.include_router(calc_router)
    app.include_router(uploads_router)
    app.include_router(functions_router)
    app.include_router(reports_router)
    app.include_router(snapshots_router)
    app.include_router(audit_router)
    app.include_router(audit_global_router)
    app.include_router(ai_tasks_router)

    # 生产期：若配置了 web_dist_dir 则挂载静态资源 + SPA fallback。
    # 必须在所有 API 路由之后挂载，避免通配符路径吞掉真实路由。
    if settings.web_dist_dir:
        _mount_web_dist(app, settings.web_dist_dir)

    return app


app = create_app()
