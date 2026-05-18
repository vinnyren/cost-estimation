"""v2.2 — /api/ai-tasks endpoints."""
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.ai_tasks import AiTaskCreate, AiTaskUpdate, AiTaskRead
from ..services import ai_tasks as svc


router = APIRouter(prefix="/api/ai-tasks", tags=["ai-tasks"])


@router.post("", response_model=AiTaskRead, status_code=201)
def create(payload: AiTaskCreate, db: Session = Depends(get_db)):
    return svc.create_task(db, payload.project_id, payload.kind)


@router.get("", response_model=list[AiTaskRead])
def list_tasks(project_id: str, db: Session = Depends(get_db)):
    return svc.list_for_project(db, project_id)


@router.get("/{task_id}", response_model=AiTaskRead)
def read_one(task_id: str, db: Session = Depends(get_db)):
    t = svc.get_task(db, task_id)
    if not t:
        raise HTTPException(404, "task not found")
    return t


@router.patch("/{task_id}", response_model=AiTaskRead)
def patch(task_id: str, payload: AiTaskUpdate, db: Session = Depends(get_db)):
    t = svc.update_task(
        db, task_id,
        status=payload.status,
        progress_pct=payload.progress_pct,
        stage_log_append=payload.stage_log_append,
        output_json=payload.output_json,
        error_message=payload.error_message,
    )
    if not t:
        raise HTTPException(404, "task not found")
    return t


@router.post("/{task_id}/start")
def start_task(task_id: str, db: Session = Depends(get_db)):
    """v2.5 — UI 触发后台 spawn claude 进程。"""
    t = svc.get_task(db, task_id)
    if not t:
        raise HTTPException(404, "task not found")
    if t.status in ("running", "done"):
        raise HTTPException(409, detail={"error": {
            "code": "TASK_ALREADY_RUNNING",
            "problem": f"task already {t.status}",
        }})

    base_url = os.environ.get("COST_BASE_URL", "http://127.0.0.1:8788")
    token = os.environ.get("COST_AUTH_TOKEN", "")
    if t.kind == "reverse_fill":
        pid = svc.spawn_claude_reverse_fill(t.id, t.project_id, base_url, token)
    else:
        pid = svc.spawn_claude_extract(t.id, t.project_id, base_url, token)
    if pid is None:
        raise HTTPException(500, detail={"error": {
            "code": "CLAUDE_CLI_UNAVAILABLE",
            "problem": "claude CLI 不在 PATH 中或未登录",
            "fix": "确认 claude 命令可用：`which claude && claude --version`",
        }})
    # /review F3: 单次 commit — 先写 pid，再 update_task 走同一事务，避免
    # status=running 已 commit 但 pid=NULL 的窗口让 /stop 误判 NO_SUBPROCESS。
    t.pid = pid
    svc.update_task(db, t.id, status="running", progress_pct=1.0,
                    stage_log_append=f"✓ 后台进程已启动 (pid={pid})")
    return {"pid": pid}


@router.post("/{task_id}/stop")
def stop_task(task_id: str, db: Session = Depends(get_db)):
    """v2.5 — kill 后台 claude 进程并标记 failed。

    /review F2: 不允许停止已完成（done）任务 — 避免把成功结果写回 failed。
    """
    t = svc.get_task(db, task_id)
    if not t:
        raise HTTPException(404, "task not found")
    if t.status == "done":
        raise HTTPException(409, detail={"error": {
            "code": "TASK_ALREADY_DONE",
            "problem": "task 已成功完成，无需停止",
        }})
    if not t.pid:
        raise HTTPException(400, detail={"error": {
            "code": "NO_SUBPROCESS",
            "problem": "task 未关联 subprocess，可能从未 /start 过",
        }})
    ok = svc.stop_claude_subprocess(t.pid)
    svc.update_task(db, t.id, status="failed",
                    error_message="用户手动停止" if ok else "停止失败 — 进程可能已退出")
    return {"stopped": ok}
