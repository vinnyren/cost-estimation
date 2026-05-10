import secrets as _secrets
from typing import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from .config import settings

ALLOWED_ORIGIN_PREFIXES = ("http://127.0.0.1", "http://localhost")


async def auth_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Token-based auth middleware (CSRF defense layer 1).

    Allows /health unauthenticated. All other paths require a token via either
    the X-Auth-Token header or the ?t= query parameter, matching settings.auth_token.

    Uses secrets.compare_digest() for constant-time comparison to mitigate timing attacks.
    """
    if request.url.path == "/health":
        return await call_next(request)
    sent = request.headers.get("X-Auth-Token") or request.query_params.get("t") or ""
    expected = settings.auth_token or ""
    if not expected:
        # 启动时未注入 token —— 防御深度
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "TOKEN_NOT_INITIALIZED",
                    "problem": "Server token missing",
                    "fix": "Restart the server with COST_AUTH_TOKEN env",
                },
            },
        )
    if not _secrets.compare_digest(sent.encode("utf-8"), expected.encode("utf-8")):
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


async def origin_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Origin allowlist middleware (CSRF defense layer 2).

    For state-changing methods (non-GET), if an Origin header is present, it must
    start with one of ALLOWED_ORIGIN_PREFIXES. GET requests are exempt; absent
    Origin is allowed (e.g. server-to-server, curl).
    """
    if request.method != "GET":
        origin = request.headers.get("Origin", "")
        if origin and not any(origin.startswith(p) for p in ALLOWED_ORIGIN_PREFIXES):
            return JSONResponse(
                status_code=403,
                content={
                    "ok": False,
                    "error": {
                        "code": "FORBIDDEN_ORIGIN",
                        "problem": f"Origin '{origin}' not allowed",
                        "fix": "Only http://127.0.0.1:* and http://localhost:* are accepted",
                    },
                },
            )
    return await call_next(request)
