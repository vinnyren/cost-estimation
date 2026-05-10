"""HTTP middleware that records mutating actions on /api/projects/* into audit_log.

Only methods PATCH/POST/PUT/DELETE under /api/projects/* are tracked. project_id
is extracted from path; action is inferred from method + sub-path. Logs are
written AFTER the response (so failures don't leave half-baked rows). For
project.create the project_id only exists *after* the response, so we drain
the response body, parse the id out, and reconstitute the response — this is
the standard Starlette pattern when the middleware needs the body.

Audit failures MUST NOT break the request: every DB call here is wrapped in
try/except, and we never re-raise.
"""
import json
import re
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..db.session import SessionLocal
from ..services import audit as svc

_PROJECT_RX = re.compile(r"^/api/projects/(?P<pid>[^/]+)(?P<sub>/?.*)$")


def _action_for(method: str, path: str) -> str | None:
    """Return action label for tracked routes. None means "ignore"."""
    if method == "POST" and path == "/api/projects":
        return "project.create"
    m = _PROJECT_RX.match(path)
    if not m:
        return None
    sub_path = m.group("sub").lstrip("/")
    if sub_path == "":
        if method == "PATCH":
            return "project.update"
        if method == "DELETE":
            return "project.delete"
        return None
    if sub_path == "copy" and method == "POST":
        return "project.copy"
    if sub_path.startswith("functions/bulk"):
        return "fp.bulk_write"
    if sub_path.startswith("functions/restore"):
        return "fp.restore"
    if sub_path.startswith("functions") and method == "POST":
        return "fp.create"
    if sub_path.startswith("functions") and method == "PATCH":
        return "fp.update"
    if sub_path.startswith("functions") and method == "DELETE":
        return "fp.delete"
    if sub_path == "params/override" and method == "PATCH":
        return "params.override"
    if sub_path.startswith("uploads") and method == "POST":
        return "upload.create"
    if sub_path.startswith("uploads") and method == "DELETE":
        return "upload.delete"
    if sub_path == "calc/forward" or sub_path == "calc/reverse":
        return "calc.run"
    if sub_path == "report/excel":
        return "report.export"
    return None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        method = request.method.upper()
        path = request.url.path
        if method not in ("POST", "PATCH", "PUT", "DELETE"):
            return await call_next(request)
        action = _action_for(method, path)
        if action is None:
            return await call_next(request)

        response = await call_next(request)
        if response.status_code < 200 or response.status_code >= 300:
            return response

        m = _PROJECT_RX.match(path)
        project_id: str | None = m.group("pid") if m else None

        if action == "project.create":
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            try:
                payload = json.loads(body.decode("utf-8") or "{}")
                project_id = payload.get("data", {}).get("id")
            except Exception:
                project_id = None
            # body_iterator is single-shot; rebuild the response so downstream
            # ASGI can stream the same bytes to the client.
            response = Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        if not project_id:
            return response

        db = SessionLocal()
        try:
            svc.write(
                db,
                project_id=project_id,
                action=action,
                target=project_id,
            )
        except Exception:
            # Audit must never break the request — swallow & move on.
            pass
        finally:
            db.close()
        return response
