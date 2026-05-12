"""v2.5 — spawn_claude_extract + stop_claude_subprocess 单测。

不真跑 claude — 用 monkeypatch 替换 subprocess.Popen 和 os.kill。
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services import ai_tasks as svc


def test_spawn_claude_returns_pid_when_claude_available(tmp_path, monkeypatch):
    """shutil.which('claude') 找到 + Popen 成功 → 返回 pid。"""
    monkeypatch.setattr("shutil.which", lambda x: "/usr/local/bin/claude" if x == "claude" else None)
    fake_proc = MagicMock()
    fake_proc.pid = 12345
    with patch("app.services.ai_tasks.subprocess.Popen", return_value=fake_proc):
        pid = svc.spawn_claude_extract(
            task_id="t-1", project_id="p-1",
            base_url="http://127.0.0.1:8788", token="testtoken",
        )
    assert pid == 12345


def test_spawn_claude_returns_none_when_claude_not_found(monkeypatch):
    """shutil.which 返回 None → spawn 返回 None。"""
    monkeypatch.setattr("shutil.which", lambda x: None)
    pid = svc.spawn_claude_extract(
        task_id="t-1", project_id="p-1",
        base_url="http://127.0.0.1:8788", token="testtoken",
    )
    assert pid is None


def test_stop_claude_subprocess_kills_running_pid(monkeypatch):
    killed = {"pid": None, "sig": None}

    def fake_kill(pid, sig):
        killed["pid"] = pid
        killed["sig"] = sig

    monkeypatch.setattr("app.services.ai_tasks.os.kill", fake_kill)
    ok = svc.stop_claude_subprocess(99999)
    assert ok is True
    assert killed["pid"] == 99999


def test_stop_claude_subprocess_returns_false_for_dead_pid(monkeypatch):
    def fake_kill(pid, sig):
        raise ProcessLookupError("no such process")

    monkeypatch.setattr("app.services.ai_tasks.os.kill", fake_kill)
    ok = svc.stop_claude_subprocess(99999)
    assert ok is False
