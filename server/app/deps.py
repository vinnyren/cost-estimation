from fastapi import Request
from fastapi.responses import JSONResponse

from .config import settings


async def auth_middleware(request: Request, call_next):
    """Token-based auth middleware (CSRF defense layer 1).

    Allows /health unauthenticated. All other paths require a token via either
    the X-Auth-Token header or the ?t= query parameter, matching settings.auth_token.
    """
    if request.url.path == "/health":
        return await call_next(request)
    sent = request.headers.get("X-Auth-Token") or request.query_params.get("t")
    if sent != settings.auth_token:
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "error": {
                    "code": "UNAUTHORIZED",
                    "problem": "Missing or invalid token",
                    "fix": "Include X-Auth-Token header or ?t= query param",
                },
            },
        )
    return await call_next(request)
