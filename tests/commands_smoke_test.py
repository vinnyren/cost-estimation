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
    assert "COST_AUTH_TOKEN" in body, \
        "必须用 COST_AUTH_TOKEN 而非 AUTH_TOKEN（与 server config env_prefix 对齐）"
    # 不应留有未加 COST_ 前缀的 AUTH_TOKEN=（行首或空白后开始的 AUTH_TOKEN=）
    import re
    bad_auth = re.search(r"(?:^|\s)AUTH_TOKEN=", body, re.MULTILINE)
    assert bad_auth is None, \
        f"不应留有未加 COST_ 前缀的 AUTH_TOKEN= ：{bad_auth.group(0)!r}"
    assert "COST_DATABASE_URL" not in body, \
        "不应使用 COST_DATABASE_URL（不存在的 setting）"


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
