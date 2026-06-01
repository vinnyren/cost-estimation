"""版本号单一来源守卫。

权威源 = .claude-plugin/plugin.json 的 version。其余生态清单文件（pyproject /
package.json / marketplace.json）各自持有的字面量必须与之一致——任一漂移即测试
失败，使版本不一致无法合并（杜绝此前 pyproject 滞留 2.6.0 而 /health 显示旧版本
的问题）。运行期读取权威源的逻辑见 app.version.get_version。
"""
import json
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _plugin_version() -> str:
    data = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text("utf-8"))
    return data["version"]


def test_pyproject_matches_plugin():
    with (REPO_ROOT / "server" / "pyproject.toml").open("rb") as f:
        ver = tomllib.load(f)["project"]["version"]
    assert ver == _plugin_version()


def test_web_package_json_matches_plugin():
    data = json.loads((REPO_ROOT / "web" / "package.json").read_text("utf-8"))
    assert data["version"] == _plugin_version()


def test_marketplace_plugin_entry_matches_plugin():
    data = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text("utf-8"))
    canonical = _plugin_version()
    assert data["plugins"][0]["version"] == canonical
    assert data["metadata"]["version"] == canonical
