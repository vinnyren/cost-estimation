import secrets

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.health import router as health_router
from .api.projects import router as projects_router
from .config import Settings, settings
from .deps import auth_middleware, origin_middleware


def create_app() -> FastAPI:
    # 重新加载 settings，使 monkeypatch 后的 env vars 生效
    # （settings 是模块级 singleton，初始 import 时已固化值，必须重新实例化以读取最新 env）
    fresh = Settings()
    settings.auth_token = fresh.auth_token  # 同步到全局，供 middleware 读取
    if not settings.auth_token:
        settings.auth_token = secrets.token_urlsafe(32)

    app = FastAPI(title="软件造价制作系统", version="1.0.0")

    # 中间件注册顺序与执行顺序相反（FastAPI prepends）：
    # - 注册顺序：CORS → origin → auth
    # - 执行顺序：auth → origin → CORS → app
    # 即：最后注册的最先执行，所以 auth 必须最后注册。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://127.0.0.1:{settings.bind_port}",
            f"http://localhost:{settings.bind_port}",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["X-Auth-Token", "Content-Type", "X-Requested-With"],
    )
    app.middleware("http")(origin_middleware)
    app.middleware("http")(auth_middleware)

    app.include_router(health_router)
    app.include_router(projects_router)
    return app


app = create_app()
