"""v2.2 — AiTask service：CRUD + 进度更新。v2.5 增加 spawn/stop 子进程函数。"""
import os
import shutil
import signal
import subprocess
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from ..db.models import AiTask


def create_task(db: Session, project_id: str, kind: str) -> AiTask:
    task = AiTask(id=str(uuid.uuid4()), project_id=project_id, kind=kind, status="queued",
                  progress_pct=0.0, stage_log="")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: str) -> AiTask | None:
    return db.query(AiTask).filter(AiTask.id == task_id).first()


def list_for_project(db: Session, project_id: str, limit: int = 10) -> list[AiTask]:
    tasks = (db.query(AiTask)
             .filter(AiTask.project_id == project_id)
             .order_by(AiTask.created_at.desc())
             .limit(limit).all())
    # v2.5 自检：running 但进程已死 → 转 failed，避免 UI 卡在 1%
    for t in tasks:
        if t.status == "running" and t.pid:
            try:
                os.kill(t.pid, 0)  # signal 0 = 探测，不发信号
            except (ProcessLookupError, PermissionError):
                t.status = "failed"
                if not t.error_message:
                    t.error_message = "后台进程异常退出 — 请查看 ai-task log"
    if any(t.status == "failed" for t in tasks):
        db.commit()
    return tasks


def update_task(
    db: Session, task_id: str, *,
    status: str | None = None,
    progress_pct: float | None = None,
    stage_log_append: str | None = None,
    output_json: str | None = None,
    error_message: str | None = None,
) -> AiTask | None:
    t = get_task(db, task_id)
    if not t:
        return None
    if status is not None:
        t.status = status
    if progress_pct is not None:
        t.progress_pct = progress_pct
    if stage_log_append is not None:
        t.stage_log = (t.stage_log or "") + stage_log_append + "\n"
    if output_json is not None:
        t.output_json = output_json
    if error_message is not None:
        t.error_message = error_message
    db.commit()
    db.refresh(t)
    return t


# ---------------------------------------------------------------------------
# v2.5 — subprocess helpers
# ---------------------------------------------------------------------------

def spawn_claude_extract(
    task_id: str,
    project_id: str,
    base_url: str,
    token: str,
) -> int | None:
    """v2.5 — 后台 spawn `claude --print` 跑 /cost <project_id>.

    Plugin /cost 命令通过 env vars (BASE/TOKEN/PROJECT_ID/TASK_ID) 6 次
    PATCH /api/ai-tasks/{id} 上报进度。本函数不等待执行完毕，立即返回 PID。

    Returns subprocess PID; None if claude CLI 不在 PATH 中。
    """
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return None

    # claude CLI 的 --allowedTools 是 variadic（吞所有后续位置参数），所以 prompt
    # 不能放在 argv 里 — 否则会被 --allowedTools 消耗，触发
    # "Input must be provided either through stdin or as a prompt argument"。
    # 改用 stdin 管道传 prompt — 更稳定且不受 flag 顺序影响。
    cmd = [
        claude_bin,
        "--print",
        "--allowed-tools",
        "Bash(curl *) Bash(jq *) Read",
    ]
    env = {
        **os.environ,
        "BASE": base_url,
        "TOKEN": token,
        "PROJECT_ID": project_id,
        "TASK_ID": task_id,
    }
    log_path = Path(os.environ.get("COST_DATA_DIR", "/tmp")) / f"ai-task-{task_id}.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_fh = open(log_path, "w")  # noqa: SIM115
    except OSError:
        log_fh = subprocess.DEVNULL  # type: ignore[assignment]

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdin=subprocess.PIPE,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    # 把 /cost <project_id> 通过 stdin 喂给 claude，再关 stdin 让 claude 看到 EOF
    try:
        assert proc.stdin is not None
        proc.stdin.write(f"/cost {project_id}\n".encode())
        proc.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    # /review F5: 关父进程持有的 log fd（子进程已 dup 一份），避免 fd 泄露
    if log_fh is not subprocess.DEVNULL:
        try:
            log_fh.close()
        except OSError:
            pass
    return proc.pid


def stop_claude_subprocess(pid: int) -> bool:
    """v2.5 — kill 后台 claude 进程 + 其派生 curl/jq 等子进程。

    spawn_claude_extract 用 start_new_session=True，子进程在独立进程组。
    用 killpg 杀整个进程组，避免 plugin /cost 派生的 curl/jq 成为孤儿进程。
    返回是否成功 (False 表示进程已不存在)。
    """
    try:
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
        return True
    except (ProcessLookupError, PermissionError):
        return False
