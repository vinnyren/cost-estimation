import secrets

from fastapi import APIRouter, FastAPI

from .api.health import router as health_router
from .config import Settings, settings
from .deps import auth_middleware


def create_app() -> FastAPI:
    # 重新加载 settings，使 monkeypatch 后的 env vars 生效
    # （settings 是模块级 singleton，初始 import 时已固化值，必须重新实例化以读取最新 env）
    fresh = Settings()
    settings.auth_token = fresh.auth_token  # 同步到全局，供 middleware 读取
    if not settings.auth_token:
        settings.auth_token = secrets.token_urlsafe(32)
    app = FastAPI(title="软件造价制作系统", version="1.0.0")
    app.middleware("http")(auth_middleware)
    app.include_router(health_router)

    # 占位 /api/projects，避免 404 干扰 token 测试
    api = APIRouter(prefix="/api")

    @api.get("/projects")
    async def _stub_projects():
        return {"ok": True, "data": []}

    app.include_router(api)
    return app


app = create_app()
