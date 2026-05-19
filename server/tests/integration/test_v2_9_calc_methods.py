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


def test_declaration_helper_covers_all_methods():
    from app.services.calc import _declaration_for
    for m in ("ifpug", "nesma_detailed", "nesma_estimated", "nesma_indicative", "cosmic"):
        decl = _declaration_for(m)
        assert isinstance(decl, str) and len(decl) > 0
