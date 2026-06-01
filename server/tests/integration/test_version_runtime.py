"""运行期版本读取：app.version.get_version 必须返回权威源 plugin.json 的值，
且 /health 端点与之一致。"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _plugin_version() -> str:
    return json.loads(
        (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text("utf-8")
    )["version"]


def test_get_version_reads_plugin_json():
    from app.version import get_version

    assert get_version() == _plugin_version()


def test_health_endpoint_reports_canonical_version():
    from app.api.health import _read_version

    assert _read_version() == _plugin_version()
