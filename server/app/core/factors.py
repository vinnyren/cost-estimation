def non_func_factor(distributed: int, performance: int, reliability: int, multi_site: int) -> float:
    """非功能因子 = (Σ) × 0.025 + 1，每项 ∈ {-1, 0, 1}"""
    for x in (distributed, performance, reliability, multi_site):
        if x not in (-1, 0, 1):
            raise ValueError(f"non_func component must be -1/0/1, got {x}")
    return (distributed + performance + reliability + multi_site) * 0.025 + 1.0


def dev_factor_chain(*, app_type: float, non_func: float, integrity: float,
                     platform: float, team_bg: float) -> float:
    """开发因子链：app × non_func × integrity × platform × team"""
    return app_type * non_func * integrity * platform * team_bg


def ops_factor_chain(*, business_importance: float, security: float, support: float,
                     update_freq: float, response: float, integrity: float,
                     platform: float, team_exp: float, deployment: float,
                     user_scale: float, relevance: float) -> float:
    """运维因子链 11 项相乘"""
    return (business_importance * security * support * update_freq * response *
            integrity * platform * team_exp * deployment * user_scale * relevance)
