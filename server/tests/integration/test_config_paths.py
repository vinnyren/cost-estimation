"""Integration: COST_DATA_DIR 必须驱动 db_path / upload_dir / parsed_dir / export_dir。

回归 v1.1 polish 发现的 MEDIUM bug：旧版 config.py 用类属性级求值
`db_path: Path = data_dir / "db" / "cost.sqlite"`，导致用户只设
COST_DATA_DIR 时，运行期 db_path 仍指向类构建期 data_dir，不会跟随
COST_DATA_DIR 变化。

修法：model_validator(mode="after") 在实例化后基于最终 data_dir 派生
四个路径，仅在字段为 None 时派生（保留 COST_DB_PATH 等显式覆盖能力）。
"""
from __future__ import annotations

import importlib


def _reload_config():
    """重新载入 app.config 让 Settings 在新环境变量下重新实例化。"""
    import app.config as cfg

    importlib.reload(cfg)
    return cfg


def test_db_path_follows_data_dir(monkeypatch, tmp_path):
    """COST_DATA_DIR 改变时，db_path / upload_dir / parsed_dir / export_dir
    应自动派生为 data_dir 的子路径。"""
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("COST_DB_PATH", raising=False)
    monkeypatch.delenv("COST_UPLOAD_DIR", raising=False)
    monkeypatch.delenv("COST_PARSED_DIR", raising=False)
    monkeypatch.delenv("COST_EXPORT_DIR", raising=False)

    cfg = _reload_config()
    s = cfg.Settings()

    assert s.data_dir == tmp_path
    assert s.db_path == tmp_path / "db" / "cost.sqlite"
    assert s.upload_dir == tmp_path / "uploads"
    assert s.parsed_dir == tmp_path / "parsed"
    assert s.export_dir == tmp_path / "exports"


def test_db_path_explicit_overrides(monkeypatch, tmp_path):
    """COST_DB_PATH 显式时应优先于派生默认值（保留覆盖能力）。"""
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    explicit = tmp_path / "custom" / "my.sqlite"
    monkeypatch.setenv("COST_DB_PATH", str(explicit))

    cfg = _reload_config()
    s = cfg.Settings()

    assert s.db_path == explicit
    # 未覆盖的字段仍按 data_dir 派生
    assert s.upload_dir == tmp_path / "uploads"


def test_upload_dir_explicit_overrides(monkeypatch, tmp_path):
    """COST_UPLOAD_DIR 显式时应优先于派生默认值。"""
    monkeypatch.setenv("COST_DATA_DIR", str(tmp_path))
    explicit_upload = tmp_path / "alt-uploads"
    monkeypatch.setenv("COST_UPLOAD_DIR", str(explicit_upload))

    cfg = _reload_config()
    s = cfg.Settings()

    assert s.upload_dir == explicit_upload
    # 未覆盖的字段仍按 data_dir 派生
    assert s.export_dir == tmp_path / "exports"
