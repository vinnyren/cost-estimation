"""Liveness/version endpoint.

路径是 GET /health（**不带** /api 前缀）— 这样 K8s / 反代健康检查无需
配置 API 路由白名单即可直连。同样原因，全局 X-Auth-Token 中间件对该
路径放行。

version 字段优先从已安装包元数据读取（pip install -e 之后），失败时
回退到读取仓库根 pyproject.toml；最终兜底 "unknown"，避免 release 时
漏改 hard-coded 字符串。
"""
from importlib.metadata import PackageNotFoundError, version as _pkg_version

from fastapi import APIRouter

router = APIRouter()


def _read_version() -> str:
    """读 pyproject 版本，避免 release 时漏改 hard-coded 字符串。"""
    try:
        return _pkg_version("cost-estimation")
    except PackageNotFoundError:
        # 包未 pip install -e 时（直接 uvicorn .venv 运行）— 读 pyproject 文件
        try:
            import tomllib
            from pathlib import Path
            here = Path(__file__).resolve()
            pyproject = here.parents[2] / "pyproject.toml"
            if pyproject.exists():
                with pyproject.open("rb") as f:
                    return tomllib.load(f)["project"]["version"]
        except Exception:
            pass
        return "unknown"


@router.get("/health")
async def health():
    return {"ok": True, "service": "cost-estimation", "version": _read_version()}
