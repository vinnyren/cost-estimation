from app.core.factors import non_func_factor, dev_factor_chain, ops_factor_chain


def test_non_func_factor_baseline():
    assert non_func_factor(0, 0, 0, 0) == 1.0


def test_non_func_factor_max():
    assert abs(non_func_factor(1, 1, 1, 1) - 1.1) < 1e-9


def test_non_func_factor_min():
    assert abs(non_func_factor(-1, -1, -1, -1) - 0.9) < 1e-9


def test_non_func_factor_invalid_value_raises():
    import pytest
    with pytest.raises(ValueError):
        non_func_factor(2, 0, 0, 0)


def test_dev_factor_chain_appendix_d():
    f = dev_factor_chain(app_type=1.0, non_func=1.0, integrity=1.0, platform=1.0, team_bg=1.0)
    assert f == 1.0


def test_ops_factor_chain_appendix_d():
    # 实施规程附录 D：1.10×1.05×0.89×0.95×1.10×1.00×1.00×1.00×1.00×1.10×1.00 ≈ 1.18
    f = ops_factor_chain(business_importance=1.10, security=1.05, support=0.89,
                         update_freq=0.95, response=1.10, integrity=1.00,
                         platform=1.00, team_exp=1.00, deployment=1.00,
                         user_scale=1.10, relevance=1.00)
    assert abs(f - 1.18) < 0.005
