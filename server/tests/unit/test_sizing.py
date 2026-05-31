"""core/sizing/ 策略包单元测试。"""
import pytest
from app.core.sizing import get_method
from app.core.sizing.ifpug import IfpugMethod
from app.core.sizing.nesma import (
    NesmaDetailedMethod, NesmaEstimatedMethod, NesmaIndicativeMethod,
)
from app.core.sizing.cosmic import CosmicMethod


class TestIfpugMethod:
    def setup_method(self):
        self.m = IfpugMethod()

    def test_size_unit(self):
        assert self.m.size_unit == "FP"

    def test_input_model(self):
        assert self.m.input_model == "ifpug_style"

    def test_ilf_with_det_ret(self):
        entry = {"category": "ILF", "det": 10, "ret": 1, "ftr": None}
        assert self.m.compute_entry_size(entry) == 7.0

    def test_ei_with_det_ftr(self):
        entry = {"category": "EI", "det": 5, "ftr": 2, "ret": None}
        assert self.m.compute_entry_size(entry) == 4.0

    def test_missing_inputs_fallback_to_average(self):
        entry = {"category": "EI", "det": None, "ftr": None, "ret": None}
        assert self.m.compute_entry_size(entry) == 4.0


class TestNesmaDetailedMethod:
    def setup_method(self):
        self.m = NesmaDetailedMethod()

    def test_size_unit_and_model(self):
        assert self.m.size_unit == "FP"
        assert self.m.input_model == "ifpug_style"

    def test_same_as_ifpug_for_ilf(self):
        entry = {"category": "ILF", "det": 10, "ret": 1, "ftr": None}
        from app.core.sizing.ifpug import IfpugMethod
        assert self.m.compute_entry_size(entry) == IfpugMethod().compute_entry_size(entry)


class TestNesmaEstimatedMethod:
    def setup_method(self):
        self.m = NesmaEstimatedMethod()

    def test_size_unit_and_model(self):
        assert self.m.size_unit == "FP"
        assert self.m.input_model == "ifpug_style"

    def test_ei_average(self):
        entry = {"category": "EI", "det": 999, "ftr": 999}
        assert self.m.compute_entry_size(entry) == 4.0

    def test_ilf_average(self):
        entry = {"category": "ILF", "det": 1, "ret": 1}
        assert self.m.compute_entry_size(entry) == 10.0

    def test_ignores_det_ret_ftr(self):
        entry = {"category": "EO", "det": None, "ftr": None}
        assert self.m.compute_entry_size(entry) == 5.0


class TestNesmaIndicativeMethod:
    def setup_method(self):
        self.m = NesmaIndicativeMethod()

    def test_size_unit_and_model(self):
        assert self.m.size_unit == "FP"
        assert self.m.input_model == "ifpug_style"

    def test_ilf_returns_35(self):
        assert self.m.compute_entry_size({"category": "ILF"}) == 35.0

    def test_eif_returns_15(self):
        assert self.m.compute_entry_size({"category": "EIF"}) == 15.0

    def test_transaction_returns_0(self):
        for cat in ("EI", "EO", "EQ"):
            assert self.m.compute_entry_size({"category": cat}) == 0.0


class TestCosmicMethod:
    def setup_method(self):
        self.m = CosmicMethod()

    def test_size_unit(self):
        assert self.m.size_unit == "CFP"

    def test_input_model(self):
        assert self.m.input_model == "cosmic"

    def test_sum_of_four_movements(self):
        entry = {"cosmic_entry": 2, "cosmic_exit": 1,
                 "cosmic_read": 3, "cosmic_write": 2}
        assert self.m.compute_entry_size(entry) == 8.0

    def test_missing_fields_treated_as_zero(self):
        entry = {"cosmic_entry": 1}
        assert self.m.compute_entry_size(entry) == 1.0

    def test_all_none_returns_zero(self):
        entry = {}
        assert self.m.compute_entry_size(entry) == 0.0


class TestGetMethod:
    def test_returns_ifpug(self):
        assert isinstance(get_method("ifpug"), IfpugMethod)

    def test_returns_nesma_detailed(self):
        assert isinstance(get_method("nesma_detailed"), NesmaDetailedMethod)

    def test_returns_nesma_estimated(self):
        assert isinstance(get_method("nesma_estimated"), NesmaEstimatedMethod)

    def test_returns_nesma_indicative(self):
        assert isinstance(get_method("nesma_indicative"), NesmaIndicativeMethod)

    def test_returns_cosmic(self):
        assert isinstance(get_method("cosmic"), CosmicMethod)

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="unknown measurement_method"):
            get_method("quick")
