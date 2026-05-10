"""校验 commands/*.md 含必要 frontmatter 与关键步骤。"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (REPO / "commands" / name).read_text(encoding="utf-8")


def test_setup_command_has_frontmatter():
    body = _read("setup.md")
    assert body.startswith("---\n")
    assert "description:" in body.split("---", 2)[1]
    assert "allowed-tools:" in body.split("---", 2)[1]


def test_cost_command_starts_uvicorn_with_token():
    body = _read("cost.md")
    assert "uvicorn" in body
    assert "127.0.0.1" in body
    assert "secrets.token_urlsafe" in body or "openssl rand" in body, \
        "必须生成随机 token"
    assert "/health" in body, "必须健康检查后再开浏览器"
    assert "/?t=" in body or "?t=$TOKEN" in body, "必须把 token 拼到 URL"


def test_cost_command_handles_port_conflict():
    body = _read("cost.md")
    # 任一形式都接受
    assert "8788" in body
    assert ".port" in body or "8789" in body, \
        "必须有备用端口或 .port 写入"


def test_cost_stop_command_kills_pid():
    body = _read("cost-stop.md")
    assert "kill" in body
    assert ".pid" in body or "pgrep" in body or "lsof" in body
