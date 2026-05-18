"""一次性初始化脚本：建立 SQLite schema + 装载 CSBMK seed。

用法：
  python -m app.bootstrap --db ~/.claude/projects/cost-estimation/db/cost.sqlite \\
                          --seed app/data/csbmk_202510.json

幂等保证：
  - 如目标 DB 已含 params_global 行，则跳过 seed 装载，不破坏用户数据。
  - 仅 create_all（不 drop），现有表与列被保留。

退出码：
  0 — 成功
  2 — seed 文件不存在
  其他非零 — 其他错误（由 click 抛出）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 注意：导入 db.session 会触发其顶层副作用（按 settings.db_path 创建一个全局
# engine）。bootstrap 自身不复用该全局 engine —— 我们按 --db 现场建一个独立
# engine，但仍需 Base 的 metadata 才能 create_all。
from app.db.session import Base
from app.db import models as _models  # noqa: F401  确保所有模型注册到 Base.metadata


def _flatten(prefix: str, obj, out: dict) -> None:
    """与 app.services.params._flatten 保持一致的扁平化策略。

    Plan 1 的服务层将 seed JSON 扁平化为多行 key/value（键以点号分层），
    bootstrap CLI 复用该约定以保证 schema 兼容。
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = obj


def reseed_if_outdated(session) -> int:
    """v2.8 — 把 params_global 里未被用户改动的行刷新到当前 csbmk JSON。

    判定与策略：
    - 删除所有 modified=False 的行，按当前 JSON 重新插入（扁平 key）。
    - modified=True 的行（用户改过）原样保留。
    - 空库 → 等价于全量 seed。
    返回重新插入的行数。
    """
    from app.config import settings
    from app.db.models import ParamGlobal

    raw = json.loads(settings.csbmk_seed_path.read_text(encoding="utf-8"))
    version = raw.get("version", "CSBMK®-unknown")
    flat: dict = {}
    _flatten("", raw, flat)

    modified_keys = {
        row.key for row in
        session.query(ParamGlobal).filter_by(modified=True).all()
    }
    session.query(ParamGlobal).filter_by(modified=False).delete()
    inserted = 0
    for k, v in flat.items():
        if k in modified_keys:
            continue  # 用户改过的 key 不动
        session.add(ParamGlobal(
            key=k, value=json.dumps(v, ensure_ascii=False),
            basis_version=version, modified=False,
        ))
        inserted += 1
    session.commit()
    return inserted


@click.command()
@click.option(
    "--db",
    "db_path",
    required=True,
    type=click.Path(path_type=Path),
    help="SQLite 数据库路径（必须）",
)
@click.option(
    "--seed",
    "seed_path",
    required=True,
    type=click.Path(path_type=Path, exists=False),
    help="CSBMK seed JSON 路径（必须）",
)
def cli(db_path: Path, seed_path: Path) -> None:
    """初始化数据库并装载 CSBMK 默认参数（幂等）。"""
    if not seed_path.exists():
        click.echo(f"错误：seed 文件不存在: {seed_path}", err=True)
        sys.exit(2)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    # 启用 WAL 与 busy_timeout（对长期共享访问更友好）
    with engine.begin() as conn:
        conn.execute(text("PRAGMA journal_mode = WAL"))
        conn.execute(text("PRAGMA busy_timeout = 5000"))
        conn.execute(text("PRAGMA foreign_keys = ON"))

    Base.metadata.create_all(engine)

    seed_json = json.loads(seed_path.read_text(encoding="utf-8"))
    version = seed_json.get("version", "CSBMK®-unknown")

    Session = sessionmaker(bind=engine)
    with Session() as session:
        existing = session.execute(
            text("SELECT count(*) FROM params_global")
        ).scalar()
        if existing and existing > 0:
            n = reseed_if_outdated(session)
            click.echo(
                f"CSBMK 参数已存在（{existing} 行）；已 re-seed 未改动项 {n} 条。"
            )
        else:
            flat: dict = {}
            _flatten("", seed_json, flat)
            params = [
                {
                    "key": k,
                    "value": json.dumps(v, ensure_ascii=False),
                    "basis_version": version,
                    "modified": False,
                }
                for k, v in flat.items()
            ]
            if params:
                session.execute(
                    text(
                        "INSERT INTO params_global "
                        "(key, value, basis_version, modified) "
                        "VALUES (:key, :value, :basis_version, :modified)"
                    ),
                    params,
                )
                session.commit()
            click.echo(
                f"✓ 已装载 CSBMK seed（版本 {version}，共 {len(params)} 条参数）。"
            )

    click.echo(f"✓ 数据库初始化完成: {db_path}")


if __name__ == "__main__":
    cli()
