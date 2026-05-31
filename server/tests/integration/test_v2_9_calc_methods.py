"""多方法 forward 计算集成测试（v2.9 A5）。"""
import pytest
from app.core.forward import ForwardInput, FpItem, calculate_forward
from app.core.context import EvaluationContext, ProjectInputs
from app.services import calc as calc_svc


def _seed_params(db):
    """Seed global params so get_effective resolves a complete cost context."""
    from app.services import params as ps
    ps.seed_from_csbmk(db=db)
    db.commit()


def _seed(db, pid: str, measurement_method: str = "nesma_estimated",
          industry: str = "全行业", city: str = "北京", phase: str = "bidding"):
    from app.db.models import Project
    p = Project(
        id=pid, name=f"calc-test-{pid}",
        project_type="dev_only", phase=phase,
        city=city, industry=industry,
        mode="forward", basis_data_ver="SSM-BK-202509",
        assessment_kind="development",
        measurement_method=measurement_method,
    )
    db.add(p)
    db.commit()
    return p


def _make_ctx(cfp_to_fp: float = 1.2) -> EvaluationContext:
    import json
    from pathlib import Path
    raw = json.loads(
        (Path(__file__).parents[2] / "app" / "data" / "ssm_bk_202509.json").read_text(encoding="utf-8")
    )
    raw["cfp_to_fp"] = cfp_to_fp
    return EvaluationContext.from_dict(
        raw, ProjectInputs(industry="全行业", city="北京", phase="bidding")
    )


class TestForwardDeclaration:
    def test_default_declaration_is_ifpug(self):
        ctx = _make_ctx()
        inp = ForwardInput(items=[FpItem(us=10.0)],
                           size_declaration="FP (IFPUG-GB/T 42449-2023)")
        result = calculate_forward(ctx, inp)
        assert result.trace["fp_count_declaration"] == "10 FP (IFPUG-GB/T 42449-2023)"

    def test_nesma_estimated_declaration(self):
        ctx = _make_ctx()
        inp = ForwardInput(items=[FpItem(us=10.0)],
                           size_declaration="FP (NESMA-GB/T 42588-2023, 估算级)")
        result = calculate_forward(ctx, inp)
        assert "NESMA" in result.trace["fp_count_declaration"]

    def test_cosmic_declaration(self):
        ctx = _make_ctx()
        inp = ForwardInput(items=[FpItem(us=10.0)],
                           size_declaration="FP 当量 (COSMIC-GB/T 42452-2023, 经 CFP 换算)")
        result = calculate_forward(ctx, inp)
        assert "COSMIC" in result.trace["fp_count_declaration"]


class TestCosmicCfpConversion:
    def test_cosmic_forward_uses_cfp_conversion(self, db_session):
        """cosmic 项目 forward：us=12 CFP, cfp_to_fp=1.2 → scale_us=10 FP 等量。"""
        from app.db.models import FunctionPoint
        _seed_params(db_session)
        _seed(db_session, "p-a5-cosmic", measurement_method="cosmic")
        db_session.add(FunctionPoint(
            id="fp-a5-cosmic-1", project_id="p-a5-cosmic", version=1,
            category="EI", complexity="average", modify_type="add",
            ufp=12, us=12,
            cosmic_entry=3, cosmic_exit=3, cosmic_read=3, cosmic_write=3,
        ))
        db_session.commit()
        result = calc_svc.run_forward(db_session, "p-a5-cosmic", {})
        assert result["scale_us"] == pytest.approx(10.0, rel=0.01)

    def test_nesma_forward_not_converted(self, db_session):
        """nesma_estimated 项目：us 直接用，不除 cfp_to_fp。"""
        from app.db.models import FunctionPoint
        _seed_params(db_session)
        _seed(db_session, "p-a5-nesma", measurement_method="nesma_estimated")
        db_session.add(FunctionPoint(
            id="fp-a5-nesma-1", project_id="p-a5-nesma", version=1,
            category="EO", complexity="average", modify_type="add",
            ufp=5, us=5,
        ))
        db_session.commit()
        result = calc_svc.run_forward(db_session, "p-a5-nesma", {})
        assert result["scale_us"] == pytest.approx(5.0, rel=0.01)


class TestCosmicReverseConversion:
    """reverse 链路按 FP/人月生产率反推规模，对 COSMIC 项目须 ×cfp_to_fp
    还原为 CFP 当量，与 forward 的 ÷cfp_to_fp 对称、与 CFP 口径的 FP 表同口径分摊。"""

    def _cfp_to_fp(self, db, pid: str) -> float:
        from app.services import params as ps
        return ps.effective_to_calc_dict(ps.get_effective(db, pid))["cfp_to_fp"]

    def test_cosmic_reverse_restores_cfp_equiv(self, db_session):
        """同 target_total 下，cosmic 项目反算规模 = nesma 项目规模 × cfp_to_fp。"""
        _seed_params(db_session)
        _seed(db_session, "p-rev-cosmic", measurement_method="cosmic")
        _seed(db_session, "p-rev-nesma", measurement_method="nesma_estimated")
        payload = {"target_total": 500.0, "other_cost": 0.0}
        r_cosmic = calc_svc.run_reverse(db_session, "p-rev-cosmic", dict(payload))
        r_nesma = calc_svc.run_reverse(db_session, "p-rev-nesma", dict(payload))
        cfp = self._cfp_to_fp(db_session, "p-rev-cosmic")
        assert cfp > 1.0  # 默认 1.2，防止种子缺失退化为 1.0
        for band in ("P10", "P50", "P90"):
            assert r_cosmic["scale_unadjusted_bands"][band] == pytest.approx(
                r_nesma["scale_unadjusted_bands"][band] * cfp, rel=0.01
            )
            assert r_cosmic["scale_adjusted_bands"][band] == pytest.approx(
                r_nesma["scale_adjusted_bands"][band] * cfp, rel=0.01
            )
        assert r_cosmic["target_ufp"] == pytest.approx(
            r_nesma["target_ufp"] * cfp, rel=0.01
        )

    def test_nesma_reverse_not_converted(self, db_session):
        """nesma 项目 reverse 规模不受 cfp_to_fp 影响（回归保护）。"""
        _seed_params(db_session)
        _seed(db_session, "p-rev-nesma2", measurement_method="nesma_estimated")
        r = calc_svc.run_reverse(
            db_session, "p-rev-nesma2", {"target_total": 500.0, "other_cost": 0.0}
        )
        # nesma 的未调整规模 = 调整后规模 × cf（cf>1），与 cfp_to_fp 无关。
        assert r["scale_unadjusted_bands"]["P50"] > 0
        assert r["target_ufp"] == pytest.approx(
            r["scale_unadjusted_bands"]["P50"], abs=0.01
        )

    def test_cosmic_reverse_module_allocation_same_unit(self, db_session):
        """带 COSMIC FP 表时，分摊 current/allocated/delta 同为 CFP 口径：
        各模块 allocated 之和应等于 CFP 当量的 target_ufp。"""
        from app.db.models import FunctionPoint
        _seed_params(db_session)
        _seed(db_session, "p-rev-cosmic-mod", measurement_method="cosmic")
        db_session.add(FunctionPoint(
            id="fp-rev-c-1", project_id="p-rev-cosmic-mod", version=1,
            category="EI", complexity="average", modify_type="add",
            subsystem="核心", l1_module="调度", l2_module="进路",
            ufp=8, us=8, cosmic_entry=2, cosmic_exit=3, cosmic_read=2, cosmic_write=1,
        ))
        db_session.add(FunctionPoint(
            id="fp-rev-c-2", project_id="p-rev-cosmic-mod", version=1,
            category="EO", complexity="average", modify_type="add",
            subsystem="核心", l1_module="统计", l2_module="报表",
            ufp=4, us=4, cosmic_entry=1, cosmic_exit=2, cosmic_read=1, cosmic_write=0,
        ))
        db_session.commit()
        r = calc_svc.run_reverse(
            db_session, "p-rev-cosmic-mod", {"target_total": 500.0, "other_cost": 0.0}
        )
        leaves = r["module_allocation"]
        assert leaves, "应有模块分摊结果"
        total_alloc = sum(leaf["allocated_ufp"] for leaf in leaves)
        assert total_alloc == pytest.approx(r["target_ufp"], rel=0.01)


def test_declaration_helper_covers_all_methods():
    from app.services.calc import _declaration_for
    for m in ("ifpug", "nesma_detailed", "nesma_estimated", "nesma_indicative", "cosmic"):
        decl = _declaration_for(m)
        assert isinstance(decl, str) and len(decl) > 0
