import json
from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..db.models import ParamGlobal, ParamOverride, Project
from ..db.session import SessionLocal


def _flatten(prefix: str, obj, out: dict) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = obj


def _unflatten(flat: dict) -> dict:
    out: dict = {}
    for key, val in flat.items():
        cur = out
        parts = key.split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = val
    return out


def seed_from_csbmk() -> None:
    raw = json.loads(settings.csbmk_seed_path.read_text(encoding="utf-8"))
    version = raw.get("version", "CSBMK®-unknown")
    flat: dict = {}
    _flatten("", raw, flat)
    db = SessionLocal()
    try:
        existing = {p.key for p in db.query(ParamGlobal).all()}
        for k, v in flat.items():
            if k in existing:
                continue
            db.add(ParamGlobal(
                key=k,
                value=json.dumps(v, ensure_ascii=False),
                basis_version=version,
                modified=False,
            ))
        db.commit()
    finally:
        db.close()


def get_global(db: Session) -> dict:
    rows = db.query(ParamGlobal).all()
    flat = {p.key: json.loads(p.value) for p in rows}
    return _unflatten(flat)


def patch_global(db: Session, key: str, value) -> None:
    p = db.query(ParamGlobal).filter_by(key=key).first()
    if p is None:
        p = ParamGlobal(
            key=key,
            value=json.dumps(value, ensure_ascii=False),
            basis_version="user",
            modified=True,
        )
        db.add(p)
    else:
        p.value = json.dumps(value, ensure_ascii=False)
        p.modified = True
    db.commit()


def reset_global(db: Session) -> None:
    """Drop ParamGlobal rows then re-seed from CSBMK file.

    Wipes anything user-modified — backs /api/params/global/reset. Per-project
    ParamOverride rows are intentionally left intact.
    """
    db.query(ParamGlobal).delete()
    db.commit()
    seed_from_csbmk()


_FLAT_TOP_KEYS = (
    "cf",
    "city_rate",
    "factors_dev",
    "factors_ops",
    "hours_per_pm",
    "ops_cost_ratio",
)


def _raw_to_flat(raw: dict) -> dict:
    """Project the seed's nested-mixed shape into the flat shape the frontend
    ParamManager consumes (productivity_dev / productivity_ops at top level)."""
    out: dict = {}
    for k in _FLAT_TOP_KEYS:
        if k in raw:
            out[k] = deepcopy(raw[k])
    productivity = raw.get("productivity") or {}
    out["productivity_dev"] = deepcopy(productivity.get("dev", {}))
    out["productivity_ops"] = deepcopy(productivity.get("ops", {}))
    return out


def _set_path(tree: dict, path: list[str], value: Any) -> None:
    cur = tree
    for p in path[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[path[-1]] = value


def get_effective(db: Session, project_id: str) -> dict:
    """Layer raw global ⊕ per-project overrides into one flat-named dict.

    Returns the projection plus an `overrides` map of just the project-specific
    keys (so the UI can render an "overridden" badge per field).
    """
    raw = get_global(db)
    eff = _raw_to_flat(raw)
    rows = db.query(ParamOverride).filter_by(project_id=project_id).all()
    overrides: dict[str, Any] = {}
    for row in rows:
        try:
            v = json.loads(row.value)
        except json.JSONDecodeError:
            v = row.value
        overrides[row.key] = v
        _set_path(eff, row.key.split("."), v)
    eff["overrides"] = overrides
    return eff


def apply_overrides(
    db: Session, project_id: str, items: dict[str, Any]
) -> dict:
    """Upsert (or delete-on-null) per-project parameter overrides.

    `items` is a flat dotted-key map. Passing `None` for a key clears that
    override row, restoring the global value.
    """
    if not db.query(Project).filter_by(id=project_id).first():
        raise ValueError("PROJECT_NOT_FOUND")
    for key, val in items.items():
        existing = (
            db.query(ParamOverride)
            .filter_by(project_id=project_id, key=key)
            .first()
        )
        if val is None:
            if existing:
                db.delete(existing)
            continue
        encoded = json.dumps(val, ensure_ascii=False)
        if existing:
            existing.value = encoded
        else:
            db.add(
                ParamOverride(
                    project_id=project_id,
                    key=key,
                    value=encoded,
                )
            )
    db.commit()
    return get_effective(db, project_id)


def effective_to_calc_dict(eff: dict) -> dict:
    """Reshape the flat effective dict back into the nested layout
    EvaluationContext.from_dict / pdr_dev / city_rate_dev all expect."""
    return {
        "cf": eff.get("cf", {}),
        "productivity": {
            "dev": eff.get("productivity_dev", {}),
            "ops": eff.get("productivity_ops", {}),
        },
        "city_rate": eff.get("city_rate", {}),
        "factors_dev": eff.get("factors_dev", {}),
        "factors_ops": eff.get("factors_ops", {}),
        "hours_per_pm": eff.get("hours_per_pm", 174),
        "ops_cost_ratio": eff.get("ops_cost_ratio", {}),
    }
