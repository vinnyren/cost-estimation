from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ProjectInputs:
    industry: str
    city: str
    phase: Literal["budget", "bidding", "planning", "change", "settled"]


@dataclass(frozen=True)
class EvaluationContext:
    raw: dict
    inputs: ProjectInputs

    @classmethod
    def from_dict(cls, params: dict, inputs: ProjectInputs) -> "EvaluationContext":
        return cls(raw=params, inputs=inputs)

    def pdr_dev(self, band: Literal["P10", "P50", "P90"]) -> float:
        return self.raw["productivity"]["dev"][self.inputs.industry][band]

    def pdr_ops(self, band: Literal["P10", "P50", "P90"]) -> float:
        return self.raw["productivity"]["ops"]["全行业"][band]

    def city_rate_dev(self) -> float:
        return self.raw["city_rate"][self.inputs.city]["dev"]

    def city_rate_ops(self) -> float:
        return self.raw["city_rate"][self.inputs.city]["ops"]

    def cf(self) -> float:
        return self.raw["cf"][self.inputs.phase]

    @property
    def hours_per_pm(self) -> float:
        return self.raw.get("hours_per_pm", 174)

    @property
    def cfp_to_fp(self) -> float:
        """COSMIC CFP → FP 当量换算系数。默认 1.2（1 NESMA-FP ≈ 1.2 CFP）。

        可在全局参数页（ParamManager）草稿编辑覆盖。
        """
        return float(self.raw.get("cfp_to_fp", 1.2))
