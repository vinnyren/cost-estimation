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
    """v2.5 fix: stub 去重 — 避免 UI + plugin 双创建同一 (project_id, kind) task。

    UI 点 "新建提取任务" → 创建 task A → /start 起 claude → plugin v2.4
    自己 POST /api/ai-tasks 又创建 task B（plugin 不读 $TASK_ID env）。

    去重判据是「progress_pct <= 1」而非时间窗口：UI 创建的 stub 在 plugin
    真正接管前一直停在 progress 0~1（/start 写 1.0），所以只要存在这样的
    queued/running stub 就复用它。claude 启动慢、plugin 几分钟后才 POST 也
    能命中 —— 比固定 30s 窗口稳。stub 一旦拿到真实进度 (>1) 或被自检翻
    failed，就不再匹配，下次是全新一轮。
    """
    existing = (db.query(AiTask)
                .filter(AiTask.project_id == project_id,
                        AiTask.kind == kind,
                        AiTask.status.in_(("queued", "running")),
                        AiTask.progress_pct <= 1.0)
                .order_by(AiTask.created_at.desc())
                .first())
    if existing:
        return existing
    task = AiTask(id=str(uuid.uuid4()), project_id=project_id, kind=kind, status="queued",
                  progress_pct=0.0, stage_log="")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: str) -> AiTask | None:
    return db.query(AiTask).filter(AiTask.id == task_id).first()


def _is_process_dead_or_zombie(pid: int) -> bool:
    """检测 pid 是否已死或处于 zombie 状态。

    os.kill(pid, 0) 对 zombie（defunct）进程仍返回成功，所以单独不够。
    用 ps 读 state 字段：Z = zombie，空 = 进程不存在。
    """
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return True
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "state="],
            capture_output=True, text=True, timeout=2,
        )
        state = result.stdout.strip()
        if not state:
            return True
        # macOS/BSD: Z = zombie; Linux: Z 或 X (dead)
        return state.startswith("Z") or state.startswith("X")
    except (subprocess.SubprocessError, OSError):
        return False  # 不确定 → 不动它


def list_for_project(db: Session, project_id: str, limit: int = 10) -> list[AiTask]:
    tasks = (db.query(AiTask)
             .filter(AiTask.project_id == project_id)
             .order_by(AiTask.created_at.desc())
             .limit(limit).all())
    # v2.5 自检：running 但进程已死/zombie → 转 failed，避免 UI 卡在 1%
    dirty = False
    for t in tasks:
        if t.status == "running" and t.pid and _is_process_dead_or_zombie(t.pid):
            t.status = "failed"
            if not t.error_message:
                t.error_message = "后台进程异常退出 — 请查看 ai-task log"
            dirty = True
    if dirty:
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

def _spawn_claude_command(
    task_id: str,
    project_id: str,
    base_url: str,
    token: str,
    command: str,
) -> int | None:
    """共享 spawn 逻辑：后台 spawn `claude --print` 并通过 stdin 喂入 command。

    Plugin 命令通过 env vars (BASE/TOKEN/PROJECT_ID/TASK_ID) PATCH /api/ai-tasks/{id}
    上报进度。本函数不等待执行完毕，立即返回 PID。

    Parameters
    ----------
    command:
        完整插件命令（不含 project_id），例如 "/cost-estimation:cost"。
        stdin 写入形如 "{command} {project_id}\\n"。

    Returns subprocess PID; None if claude CLI 不在 PATH 中。
    """
    claude_bin = shutil.which("claude")
    if not claude_bin:
        return None

    # claude CLI 的 --allowed-tools 是 variadic（吞所有后续位置参数），所以 prompt
    # 不能放在 argv 里 — 否则会被消耗，触发
    # "Input must be provided either through stdin or as a prompt argument"。
    # 改用 stdin 管道传 prompt。
    #
    # 工具白名单给整个 Bash —— plugin /cost 的 Branch B 要跑 cat/lsof/mkdir/
    # curl/jq 等命令；窄白名单 "Bash(curl *)" 会拦掉 cat .port 这类读取，
    # 在 --print 非交互模式下被自动拒绝 → plugin 卡死、零进度。
    # plugin cost.md frontmatter 自身声明 allowed-tools: Bash, Read。
    cmd = [
        claude_bin,
        "--print",
        "--allowed-tools",
        "Bash Read",
    ]
    # 注入 NO_PROXY：环境若配了 http_proxy（如公司代理），plugin 的 curl 不带
    # --noproxy 会把 127.0.0.1 也走代理 → 502。把 localhost 加进 NO_PROXY 让
    # curl 绕过代理直连本地后端。保留用户已有的 NO_PROXY 条目。
    _local_hosts = "127.0.0.1,localhost"
    _existing_np = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    _no_proxy = f"{_existing_np},{_local_hosts}".strip(",") if _existing_np else _local_hosts
    env = {
        **os.environ,
        "BASE": base_url,
        "TOKEN": token,
        "PROJECT_ID": project_id,
        "TASK_ID": task_id,
        "NO_PROXY": _no_proxy,
        "no_proxy": _no_proxy,
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
    # 把 "{command} {project_id}" 通过 stdin 喂给 claude。
    # 注：必须用插件命名空间 (cost-estimation:*)，否则裸命令（如 `/cost`）会被
    # claude 内置命令截获，导致 plugin 永远不执行。
    try:
        assert proc.stdin is not None
        proc.stdin.write(f"{command} {project_id}\n".encode())
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


def spawn_claude_extract(
    task_id: str,
    project_id: str,
    base_url: str,
    token: str,
) -> int | None:
    """v2.5 — 后台 spawn `claude --print` 跑 /cost-estimation:cost <project_id>.

    Plugin /cost 命令通过 env vars (BASE/TOKEN/PROJECT_ID/TASK_ID) 6 次
    PATCH /api/ai-tasks/{id} 上报进度。本函数不等待执行完毕，立即返回 PID。

    Returns subprocess PID; None if claude CLI 不在 PATH 中。
    """
    return _spawn_claude_command(task_id, project_id, base_url, token,
                                 "/cost-estimation:cost")


def spawn_claude_reverse_fill(
    task_id: str,
    project_id: str,
    base_url: str,
    token: str,
) -> int | None:
    """v2.8 — 后台 spawn `claude --print` 跑 /cost-estimation:cost-fill <project_id>.

    与 spawn_claude_extract 同构（env vars + stdin 喂命令），仅命令不同：
    cost-fill 命令读反算模块树缺口、生成补全 FP 草稿写回 FP 表。
    Returns subprocess PID; None if claude CLI 不在 PATH 中。
    """
    return _spawn_claude_command(task_id, project_id, base_url, token,
                                 "/cost-estimation:cost-fill")


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
