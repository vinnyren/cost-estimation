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
    """Write a single global param override. Key must resolve to an existing
    leaf in the canonical tree (see _path_resolves_to_leaf); rejects pollution
    like {"key": "anything", "value": 1} that would otherwise add a stray
    row visible to every project."""
    raw_eff = _raw_to_flat(get_global(db))
    if not _path_resolves_to_leaf(raw_eff, key):
        raise ValueError(
            f"INVALID_PARAM_KEY: {key!r} does not resolve to a known leaf"
        )
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
    """Drop ParamGlobal rows then re-seed from CSBMK file in a single
    transaction.

    Wipes anything user-modified — backs /api/params/global/reset. Per-project
    ParamOverride rows are intentionally left intact.

    /review round 5: 之前 delete+commit 然后 seed_from_csbmk 用独立 session
    打开了一个空 params 窗口，并发 calc 会拿空树。改为 inline 重新 seed 在
    同一 session 同一 transaction 中提交，避免 reader 看到过渡空状态。
    """
    raw = json.loads(settings.csbmk_seed_path.read_text(encoding="utf-8"))
    version = raw.get("version", "CSBMK®-unknown")
    flat: dict = {}
    _flatten("", raw, flat)
    db.query(ParamGlobal).delete()
    for k, v in flat.items():
        db.add(ParamGlobal(
            key=k,
            value=json.dumps(v, ensure_ascii=False),
            basis_version=version,
            modified=False,
        ))
    db.commit()


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


_KEY_MAX_LEN = 256


def _path_resolves_to_leaf(tree: dict, key: str) -> bool:
    """A param-override key is well-formed only when it refers to a non-dict
    leaf in the canonical params tree. Otherwise the user can clobber an
    entire subtree (e.g. POST {"cf": 42} overwrites the whole cf dict and
    crashes the next forward calc). /review round 5 adversarial discovery."""
    if not isinstance(key, str) or not (1 <= len(key) <= _KEY_MAX_LEN):
        return False
    parts = key.split(".")
    if any(not p for p in parts):
        return False
    cur: Any = tree
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return False
        cur = cur[p]
    return not isinstance(cur, dict)


def validate_override_key(db: Session, key: str) -> None:
    """Raise ValueError if key is unsafe to write into ParamOverride / ParamGlobal."""
    raw = get_global(db)
    eff = _raw_to_flat(raw)
    if not _path_resolves_to_leaf(eff, key):
        raise ValueError(
            f"INVALID_PARAM_KEY: {key!r} does not resolve to a known leaf "
            f"(must be a dotted path ending at a scalar in the params tree)"
        )


def apply_overrides(
    db: Session, project_id: str, items: dict[str, Any]
) -> dict:
    """Upsert (or delete-on-null) per-project parameter overrides.

    `items` is a flat dotted-key map. Passing `None` for a key clears that
    override row, restoring the global value.

    Each key is validated against the canonical params tree so users can't
    overwrite a top-level subtree (e.g. {"cf": 42} would otherwise flatten
    the whole cf dict to a scalar — see /review round 5).

    Marks any cached Result rows stale — calc engine reads effective(=global
    ⊕ overrides), so changing an override invalidates the previously computed
    cost (ISSUE-011). Today the calc path doesn't actually persist Result
    rows, so this is a no-op in practice; wiring it now keeps the path
    correct when result caching is added.
    """
    from ..db.models import Result
    if not db.query(Project).filter_by(id=project_id).first():
        raise ValueError("PROJECT_NOT_FOUND")
    raw_eff = _raw_to_flat(get_global(db))
    for key in items:
        if not _path_resolves_to_leaf(raw_eff, key):
            raise ValueError(
                f"INVALID_PARAM_KEY: {key!r} does not resolve to a known leaf"
            )
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
    db.query(Result).filter_by(project_id=project_id).update(
        {Result.is_stale: True}
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


def _leaf_paths(d: dict, prefix: str = "") -> list[tuple[str, Any]]:
    """Walk a nested dict and return [(dotted.path, leaf_value), ...].

    Used by services.snapshots.restore_snapshot to replay a captured params
    payload back into ParamGlobal / ParamOverride one leaf at a time so the
    existing patch_global / apply_overrides validation paths catch any leaf
    that no longer maps onto the canonical tree (e.g. a stale CSBMK version).
    """
    out: list[tuple[str, Any]] = []
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            out.extend(_leaf_paths(v, path))
        else:
            out.append((path, v))
    return out
