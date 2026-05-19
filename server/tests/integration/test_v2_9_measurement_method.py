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


from app.schemas.project import ProjectCreate, ProjectPatch
from app.schemas.functions import FunctionPointBase, FunctionPointPatch


def test_project_create_measurement_method_default():
    """ProjectCreate 默认 measurement_method = nesma_estimated。"""
    p = ProjectCreate(
        name="test", city="北京", industry="全行业", phase="bidding",
        project_type="dev_only", assessment_kind="development",
        mode="forward", basis_data_ver="CSBMK®-202510",
    )
    assert p.measurement_method == "nesma_estimated"


def test_project_create_cosmic_method():
    """ProjectCreate 接受 measurement_method = cosmic。"""
    p = ProjectCreate(
        name="cosmic-proj", city="北京", industry="全行业", phase="bidding",
        project_type="dev_only", assessment_kind="development",
        mode="forward", basis_data_ver="CSBMK®-202510",
        measurement_method="cosmic",
    )
    assert p.measurement_method == "cosmic"


def test_project_patch_measurement_method_optional():
    """ProjectPatch 的 measurement_method 是 Optional，可不传。"""
    patch = ProjectPatch()
    assert patch.measurement_method is None
    patch2 = ProjectPatch(measurement_method="ifpug")
    assert patch2.measurement_method == "ifpug"


def test_fp_base_cosmic_fields_default_none():
    """FunctionPointBase 的 cosmic_* 字段默认 None。"""
    fp = FunctionPointBase(category="EI", complexity="average", ufp=4.0, us=4.0)
    assert fp.cosmic_entry is None
    assert fp.cosmic_exit is None
    assert fp.cosmic_read is None
    assert fp.cosmic_write is None


def test_fp_base_cosmic_fields_set():
    """FunctionPointBase 可设置 cosmic_* 字段（非负整数）。"""
    fp = FunctionPointBase(
        category="EI", complexity="average", ufp=4.0, us=4.0,
        cosmic_entry=2, cosmic_exit=1, cosmic_read=3, cosmic_write=2,
    )
    assert fp.cosmic_entry == 2
    assert fp.cosmic_write == 2


def test_fp_patch_cosmic_fields():
    """FunctionPointPatch 支持 cosmic_* 可选字段。"""
    patch = FunctionPointPatch(cosmic_entry=1, cosmic_exit=2)
    assert patch.cosmic_entry == 1
    assert patch.cosmic_read is None
