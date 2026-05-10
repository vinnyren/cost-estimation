"""校验 .claude-plugin/*.json 是否符合 Claude Code plugin 规范。"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(path: str) -> dict:
    return json.loads((REPO / path).read_text(encoding="utf-8"))


def test_marketplace_json_required_fields():
    m = _load(".claude-plugin/marketplace.json")
    assert m["name"] == "cost-estimation-marketplace"
    assert "owner" in m and m["owner"]["name"]
    assert "metadata" in m and m["metadata"]["version"] == "1.0.0"
    assert isinstance(m["plugins"], list) and len(m["plugins"]) >= 1
    plugin = m["plugins"][0]
    assert plugin["name"] == "cost-estimation"
    assert plugin["source"]["source"] == "url"
    assert plugin["source"]["url"].startswith("https://")
    assert plugin["strict"] is True


def test_plugin_json_lists_three_commands():
    p = _load(".claude-plugin/plugin.json")
    assert p["name"] == "cost-estimation"
    assert p["version"] == "1.0.0"
    cmd_paths = p["commands"]
    assert "./commands/setup.md" in cmd_paths
    assert "./commands/cost.md" in cmd_paths
    assert "./commands/cost-stop.md" in cmd_paths
    assert p["license"] == "MIT"
    assert "cost-estimation" in p["keywords"]
    assert "GB-T-36964" in p["keywords"]


def test_directory_skeleton_exists():
    """T1 后必备目录骨架。"""
    for d in (".claude-plugin", "commands", "reference", "tests/e2e"):
        assert (REPO / d).is_dir(), f"missing dir: {d}"
