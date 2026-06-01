#!/usr/bin/env python3
"""版本号单一来源 — 一处改、全量同步。

权威源 = .claude-plugin/plugin.json 的 version。本脚本把新版本写入 plugin.json
并同步到其余生态清单字面量（marketplace.json / server pyproject.toml /
web package.json）。运行期读取见 server/app/version.py 与 web 的 __APP_VERSION__。

用法：
  python scripts/bump-version.py 2.10.0      # 写入新版本并同步
  python scripts/bump-version.py --check     # 只校验各处是否一致（CI/本地守卫）

校验同样由 server/tests/integration/test_version_single_source.py 强制。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PYPROJECT = REPO_ROOT / "server" / "pyproject.toml"
PACKAGE_JSON = REPO_ROOT / "web" / "package.json"

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _canonical() -> str:
    return json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]


def _read_json_version(path: Path, *keys) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    for k in keys:
        data = data[k]
    return data


def _read_pyproject_version() -> str:
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', PYPROJECT.read_text(encoding="utf-8"))
    if not m:
        raise ValueError("pyproject.toml 未找到 version")
    return m.group(1)


def check() -> int:
    canonical = _canonical()
    sources = {
        "marketplace.json[plugins[0]]": _read_json_version(MARKETPLACE_JSON, "plugins", 0, "version"),
        "marketplace.json[metadata]": _read_json_version(MARKETPLACE_JSON, "metadata", "version"),
        "server/pyproject.toml": _read_pyproject_version(),
        "web/package.json": _read_json_version(PACKAGE_JSON, "version"),
    }
    drift = {name: v for name, v in sources.items() if v != canonical}
    if drift:
        print(f"✗ 版本漂移（权威源 plugin.json = {canonical}）：")
        for name, v in drift.items():
            print(f"  - {name} = {v}")
        return 1
    print(f"✓ 版本一致：{canonical}")
    return 0


def _replace_json_version(path: Path, new: str, *keys) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    node = data
    for k in keys[:-1]:
        node = node[k]
    node[keys[-1]] = new
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bump(new: str) -> int:
    if not _SEMVER.match(new):
        print(f"✗ 版本号格式应为 X.Y.Z，收到：{new}")
        return 1
    _replace_json_version(PLUGIN_JSON, new, "version")
    _replace_json_version(MARKETPLACE_JSON, new, "plugins", 0, "version")
    _replace_json_version(MARKETPLACE_JSON, new, "metadata", "version")
    _replace_json_version(PACKAGE_JSON, new, "version")
    text = PYPROJECT.read_text(encoding="utf-8")
    text = re.sub(r'(?m)^(version\s*=\s*)"[^"]+"', rf'\g<1>"{new}"', text, count=1)
    PYPROJECT.write_text(text, encoding="utf-8")
    print(f"✓ 已将版本同步为 {new}（plugin.json / marketplace.json / pyproject.toml / package.json）")
    print("  运行期：后端 app.version.get_version 读 plugin.json；前端 __APP_VERSION__ 构建期注入。")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    arg = argv[0]
    if arg == "--check":
        return check()
    return bump(arg)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
