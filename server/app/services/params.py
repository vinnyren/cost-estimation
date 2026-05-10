import json
from sqlalchemy.orm import Session

from ..config import settings
from ..db.models import ParamGlobal
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
