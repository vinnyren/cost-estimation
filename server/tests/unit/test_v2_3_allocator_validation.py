"""v2.3 — allocate_with_validation 返回 envelope {items, validation}."""
from app.core.allocator import allocate_with_validation, AllocatorInput, FpDraft


def test_allocate_with_validation_envelope():
    inp = AllocatorInput(
        target_us=275.0,
        cf=1.21,
        drafts=[
            FpDraft(name="前端", weight=1.0),
            FpDraft(name="后端", weight=1.5),
        ],
    )
    res = allocate_with_validation(inp)
    assert "items" in res
    assert "validation" in res
    assert len(res["items"]) == 2
    assert isinstance(res["validation"]["error_pct"], float)
    assert isinstance(res["validation"]["recalc_total_us"], float)
    # 权重比 1:1.5 → us 比也应是 1:1.5
    us_qian = next(o.us for o in res["items"] if o.name == "前端")
    us_hou = next(o.us for o in res["items"] if o.name == "后端")
    assert abs(us_hou / us_qian - 1.5) < 0.01
    # 一致性 — 总 us 累加 ≈ target_us / cf (因为 us 是 unadjusted)
    total_us = sum(o.us for o in res["items"])
    expected_us = 275.0 / 1.21
    assert abs(total_us - expected_us) < 1.0


def test_validation_error_pct_under_1_for_normal_allocation():
    inp = AllocatorInput(
        target_us=500.0, cf=1.21,
        drafts=[FpDraft(name="A", weight=1.0), FpDraft(name="B", weight=2.0)],
    )
    res = allocate_with_validation(inp)
    # 没有 locked + 没有 rounding precision loss 时 error_pct 应接近 0
    assert res["validation"]["error_pct"] < 1.0
