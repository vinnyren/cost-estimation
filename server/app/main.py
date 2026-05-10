import secrets
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.health import router as health_router
from .api.projects import router as projects_router
from .api.params import router as params_router
from .api.calc import router as calc_router
from .config import Settings, settings
from .deps import auth_middleware, origin_middleware


def create_app() -> FastAPI:
    fresh = Settings()
    settings.auth_token = fresh.auth_token
    if not settings.auth_token:
        settings.auth_token = secrets.token_urlsafe(32)

    app = FastAPI(title="软件造价制作系统", version="1.0.0")

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

    app.include_router(health_router)
    app.include_router(projects_router)
    app.include_router(params_router)
    app.include_router(calc_router)

    @app.on_event("startup")
    async def _bootstrap() -> None:
        from .db.session import Base, engine
        from .services.params import seed_from_csbmk
        Base.metadata.create_all(bind=engine)
        seed_from_csbmk()

    return app


app = create_app()
