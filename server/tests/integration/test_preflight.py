"""集成：preflight 检测 Python 版本、libmagic、pip 镜像可达性。"""
from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner


def test_preflight_passes_on_supported_python():
    from app.preflight import cli

    runner = CliRunner()
    result = runner.invoke(cli, [])
    # 当前 venv 已经满足，预期 exit 0 或 warning（但非 fatal）
    assert result.exit_code == 0
    assert "Python" in result.output


def test_preflight_fails_on_old_python(monkeypatch):
    from app import preflight

    monkeypatch.setattr(preflight.sys, "version_info", (3, 9, 0, "final", 0))
    runner = CliRunner()
    result = runner.invoke(preflight.cli, [])
    assert result.exit_code != 0
    assert "3.11" in result.output


def test_preflight_warns_when_libmagic_missing():
    from app import preflight

    with patch.object(preflight, "_find_libmagic", return_value=None):
        runner = CliRunner()
        result = runner.invoke(preflight.cli, [])
        assert result.exit_code != 0
        assert "libmagic" in result.output.lower()
