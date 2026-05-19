from app.db.models import (
    FPSnapshot,
    FunctionPoint,
    ParamGlobal,
    ParamOverride,
    Project,
    Result,
    Upload,
)


def test_project_required_fields():
    fields = {c.name for c in Project.__table__.columns}
    must_have = {
        "id",
        "name",
        "created_at",
        "updated_at",
        "project_type",
        "phase",
        "city",
        "industry",
        "client",
        "evaluator",
        "mode",
        "target_cost",
        "other_cost",
        "include_ops",
        "alpha_dev",
        "measurement_method",
        "basis_data_ver",
    }
    assert must_have.issubset(fields)


def test_function_point_required_fields():
    fields = {c.name for c in FunctionPoint.__table__.columns}
    must_have = {
        "id",
        "project_id",
        "version",
        "subsystem",
        "l1_module",
        "l2_module",
        "description",
        "name",
        "category",
        "complexity",
        "ufp",
        "reuse_level",
        "modify_type",
        "us",
        "source",
        "locked",
        "notes",
        "ord",
    }
    assert must_have.issubset(fields)


def test_fp_snapshot_required_fields():
    fields = {c.name for c in FPSnapshot.__table__.columns}
    must_have = {"id", "project_id", "version", "snapshot_at", "snapshot_json", "reason"}
    assert must_have.issubset(fields)


def test_param_global_required_fields():
    fields = {c.name for c in ParamGlobal.__table__.columns}
    must_have = {"key", "value", "basis_version", "modified", "updated_at"}
    assert must_have.issubset(fields)


def test_param_override_required_fields():
    fields = {c.name for c in ParamOverride.__table__.columns}
    must_have = {"project_id", "key", "value", "reason", "updated_at"}
    assert must_have.issubset(fields)


def test_result_required_fields():
    fields = {c.name for c in Result.__table__.columns}
    must_have = {
        "id",
        "project_id",
        "computed_at",
        "mode",
        "fp_version",
        "params_hash",
        "payload_json",
        "is_stale",
    }
    assert must_have.issubset(fields)


def test_upload_required_fields():
    fields = {c.name for c in Upload.__table__.columns}
    must_have = {
        "id",
        "project_id",
        "filename",
        "size",
        "uploaded_at",
        "filetype",
        "parsed_text_path",
    }
    assert must_have.issubset(fields)
