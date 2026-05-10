import secrets

from fastapi import FastAPI

from .api.health import router as health_router
from .config import settings


def create_app() -> FastAPI:
    if not settings.auth_token:
        settings.auth_token = secrets.token_urlsafe(32)
    app = FastAPI(title="软件造价制作系统", version="1.0.0")
    app.include_router(health_router)
    return app


app = create_app()
