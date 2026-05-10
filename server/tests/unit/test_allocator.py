import pytest
from app.core.allocator import allocate, AllocatorInput, FpDraft


def test_allocator_simple_proportional():
    drafts = [FpDraft(name="A", weight=4, locked=False),
              FpDraft(name="B", weight=10, locked=False),
              FpDraft(name="C", weight=4, locked=False)]
    out = allocate(AllocatorInput(target_us=180, drafts=drafts, cf=1.21))
    # 总和 ≈ 180/1.21 ≈ 148.76（未调整 us 单位之和）
    total_us = sum(o.us for o in out)
    expected_total = round(180 / 1.21, 2)
    assert abs(total_us - expected_total) < 0.05
    a = next(o for o in out if o.name == "A")
    assert a.audit_tag == "budget_derived"


def test_allocator_with_locked_items():
    drafts = [FpDraft(name="L", weight=20, locked=True, locked_us=20),
              FpDraft(name="X", weight=10, locked=False),
              FpDraft(name="Y", weight=10, locked=False)]
    # target_us=80（S 单位），locked 占 20 × 1.21 = 24.2
    # s_free = 80 - 24.2 = 55.8 → /1.21 = 46.12 给 X+Y
    out = allocate(AllocatorInput(target_us=80, drafts=drafts, cf=1.21))
    locked_out = next(o for o in out if o.name == "L")
    assert locked_out.us == 20
    assert locked_out.audit_tag is None
    free_us_total = sum(o.us for o in out if not o.locked)
    expected_free = round((80 - 20 * 1.21) / 1.21, 2)
    assert abs(free_us_total - expected_free) < 0.05


def test_allocator_locked_exceeds_target_raises():
    drafts = [FpDraft(name="L", weight=100, locked=True, locked_us=100)]
    with pytest.raises(ValueError, match="LOCKED_EXCEEDS_TARGET"):
        allocate(AllocatorInput(target_us=50, drafts=drafts, cf=1.21))
