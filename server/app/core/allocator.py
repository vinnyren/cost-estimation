from dataclasses import dataclass


@dataclass
class FpDraft:
    name: str
    weight: float
    locked: bool = False
    locked_us: float = 0.0  # 仅 locked=True 时使用


@dataclass
class AllocatorInput:
    target_us: float                # 调整后目标 S
    drafts: list[FpDraft]
    cf: float


@dataclass
class AllocatorOutput:
    name: str
    us: float
    locked: bool
    audit_tag: str | None     # "budget_derived" | None


def allocate(inp: AllocatorInput) -> list[AllocatorOutput]:
    locked_us_sum = sum(d.locked_us for d in inp.drafts if d.locked)
    s_locked = locked_us_sum * inp.cf
    s_free = inp.target_us - s_locked
    if s_free <= 0:
        raise ValueError(f"LOCKED_EXCEEDS_TARGET: locked={s_locked}, target={inp.target_us}")
    free = [d for d in inp.drafts if not d.locked]
    weight_sum = sum(d.weight for d in free) or 1.0
    out: list[AllocatorOutput] = []
    for d in inp.drafts:
        if d.locked:
            out.append(AllocatorOutput(name=d.name, us=d.locked_us, locked=True, audit_tag=None))
        else:
            us = round(s_free / inp.cf * d.weight / weight_sum, 2)
            out.append(AllocatorOutput(name=d.name, us=us, locked=False, audit_tag="budget_derived"))
    return out


def allocate_with_validation(inp: AllocatorInput) -> dict:
    """v2.3 — 返回 {items, validation} envelope；items 同 allocate() 输出，
    validation.error_pct 是反算 forward 重算总规模与 target_us 的误差比例（%）。
    """
    items = allocate(inp)
    total_us = sum(o.us for o in items)
    recalc_total_adjusted = total_us * inp.cf
    error_abs = abs(recalc_total_adjusted - inp.target_us)
    error_pct = (error_abs / inp.target_us * 100) if inp.target_us > 0 else 0.0
    return {
        "items": items,
        "validation": {
            "recalc_total_us": total_us,
            "recalc_total_adjusted": recalc_total_adjusted,
            "error_pct": round(error_pct, 3),
        },
    }
