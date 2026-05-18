"""v2.8 — ParamGlobal reset+re-seed 迁移：旧库刷新到新 csbmk JSON。"""
import json
from app.db.models import ParamGlobal
from app.bootstrap import reseed_if_outdated


def _insert_stale(db, key, value, version="CSBMK®-202510", modified=False):
    db.add(ParamGlobal(key=key, value=json.dumps(value, ensure_ascii=False),
                        basis_version=version, modified=modified))
    db.commit()


def test_reseed_refreshes_unmodified_keys(db_session):
    # 旧库里 modify 因子是旧值 0.70
    _insert_stale(db_session, "scale_change.modify", 0.70)
    reseed_if_outdated(db_session)
    row = db_session.query(ParamGlobal).filter_by(key="scale_change.modify").first()
    # 新 JSON 是 0.80
    assert json.loads(row.value) == 0.80


def test_reseed_preserves_user_modified_keys(db_session):
    # 用户改过 city_rate.北京.dev → modified=True，不应被覆盖
    _insert_stale(db_session, "city_rate.北京.dev", 99999, modified=True)
    _insert_stale(db_session, "scale_change.modify", 0.70, modified=False)
    reseed_if_outdated(db_session)
    user_row = db_session.query(ParamGlobal).filter_by(key="city_rate.北京.dev").first()
    assert json.loads(user_row.value) == 99999  # 用户改动保留
    sc_row = db_session.query(ParamGlobal).filter_by(key="scale_change.modify").first()
    assert json.loads(sc_row.value) == 0.80  # 未改动 key 被刷新


def test_reseed_idempotent_on_fresh_db(db_session):
    # 空库 → 全量 seed，不报错
    reseed_if_outdated(db_session)
    n = db_session.query(ParamGlobal).count()
    assert n > 0
    # 再跑一次不重复插入也不报错
    reseed_if_outdated(db_session)
    assert db_session.query(ParamGlobal).count() == n
