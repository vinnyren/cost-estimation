"""应用版本单一来源读取。

权威源 = 插件根的 `.claude-plugin/plugin.json` 的 `version` 字段。后端运行期
（无论是否 pip 安装）一律从该文件读取，避免硬编码版本与权威源漂移——这是
版本号"单一来源"的运行期落点。

布局适配（均为 `parents[2] / .claude-plugin / plugin.json`）：
- 源码仓库：    <repo>/server/app/version.py  ↔  <repo>/.claude-plugin/plugin.json
- marketplace： <root>/server/app/version.py  ↔  <root>/.claude-plugin/plugin.json
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_version() -> str:
    """读取权威源 plugin.json 的版本；读不到时回退 'unknown'。"""
    plugin_json = Path(__file__).resolve().parents[2] / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(plugin_json.read_text(encoding="utf-8"))["version"]
    except (OSError, KeyError, json.JSONDecodeError):
        return "unknown"
