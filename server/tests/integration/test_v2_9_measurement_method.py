"""v2.9 migration：measurement_method 列 + COSMIC 列测试。

Task A1 覆盖：Project 有 measurement_method / 无 fp_method；
FunctionPoint 有 4 个 cosmic_* 列。
Task A3 扩展：同文件后续追加 schema 和 PATCH 测试。
Task A4 扩展：同文件后续追加 _apply_sizing HTTP 测试。
"""
import pytest
from sqlalchemy import inspect as sa_inspect
from app.db.models import Project, FunctionPoint

H = {"X-Auth-Token": "test-secret-token-xyz", "Origin": "http://127.0.0.1:8788"}


def test_project_has_measurement_method(db_session):
    """Project model 应有 measurement_method 列，不再有 fp_method。"""
    cols = {c.name for c in Project.__table__.columns}
    assert "measurement_method" in cols
    assert "fp_method" not in cols


def test_fp_has_cosmic_columns(db_session):
    """FunctionPoint model 应有 4 个 cosmic_* 整数可空列。"""
    cols = {c.name: c for c in FunctionPoint.__table__.columns}
    for col_name in ("cosmic_entry", "cosmic_exit", "cosmic_read", "cosmic_write"):
        assert col_name in cols, f"缺列 {col_name}"
        assert cols[col_name].nullable is True, f"{col_name} 应可空"
