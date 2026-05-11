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

        # 把 path 的 sub_path（去掉 /api/projects/{id}/ 前缀部分）+ query 参数
        # 序列化进 audit context。后续审计需要还原"哪条具体操作"时不需要从 log
        # 文件回溯 — 例 fp.restore 的 version、calc.run 的 mode、bulk_write 的
        # replace flag 都会被记录。Review finding #2。
        sub_path = m.group("sub").lstrip("/") if m else ""
        query_params = dict(request.query_params)
        # 不要记 t= (auth token via query)
        query_params.pop("t", None)
        audit_context: dict = {}
        if sub_path:
            audit_context["sub_path"] = sub_path
        if query_params:
            audit_context["query"] = query_params

        # 对 create 和 copy 都需要从响应 body 取新生成的 project id。
        # 注意：此处 body 缓冲假定响应是一次性 JSON（FastAPI JSONResponse 的默认
        # 行为）。如果未来给 `/api/projects` POST 或 `/api/projects/{id}/copy` 加
        # 流式响应（SSE / file download），需要把这个路径加白名单跳过，否则客户
        # 端会拿不到 streaming 直到 buffer 满。
        copy_target_id: str | None = None
        if action in ("project.create", "project.copy"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            try:
                payload = json.loads(body.decode("utf-8") or "{}")
                new_id = payload.get("data", {}).get("id")
            except Exception:
                new_id = None
            if action == "project.create":
                project_id = new_id
            elif action == "project.copy":
                # 源项目 ID 已在 path 里；副本 ID 从 body 取
                copy_target_id = new_id
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
            # 主 audit 行：source/创建/普通操作记到 project_id
            target = copy_target_id or project_id
            main_diff = audit_context or None
            svc.write(
                db,
                project_id=project_id,
                action=action,
                target=target,
                diff_json=(
                    json.dumps(main_diff, ensure_ascii=False) if main_diff else None
                ),
            )
            # BUG-03: 副本项目自己也需要一条 audit 入口，否则它的时间线是空的
            if action == "project.copy" and copy_target_id:
                svc.write(
                    db,
                    project_id=copy_target_id,
                    action="project.create",
                    target=copy_target_id,
                    diff_json=json.dumps(
                        {"copied_from": project_id}, ensure_ascii=False
                    ),
                )
        except Exception:
            # Audit must never break the request — swallow & move on.
            pass
        finally:
            db.close()
        return response
