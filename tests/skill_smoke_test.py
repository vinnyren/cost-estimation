"""校验 SKILL.md 与 reference/*.md 含关键内容。"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_skill_md_frontmatter():
    body = _read("SKILL.md")
    assert body.startswith("---\n")
    head = body.split("---", 2)[1]
    assert "name: cost-estimation" in head
    assert "description:" in head


def test_skill_md_describes_trigger_phrases():
    body = _read("SKILL.md")
    for phrase in ("造价评估", "功能点", "/cost"):
        assert phrase in body


def test_skill_md_says_no_for_dangerous_actions():
    body = _read("SKILL.md")
    assert "不要" in body or "不在" in body
    # 不修改 params_global
    assert "params_global" in body
    # 不直接生成 Excel
    assert "Excel" in body


def test_nesma_rules_has_5_categories():
    body = _read("reference/nesma-rules.md")
    for cat in ("EI", "EO", "EQ", "ILF", "EIF"):
        assert cat in body, f"missing category: {cat}"


def test_csbmk_overview_documents_six_industries():
    body = _read("reference/csbmk-overview.md")
    for ind in ("电子政务", "金融", "电信", "制造", "能源", "交通"):
        assert ind in body, f"missing industry: {ind}"
