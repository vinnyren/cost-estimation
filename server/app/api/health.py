"""Liveness/version endpoint.

路径是 GET /health（**不带** /api 前缀）— 这样 K8s / 反代健康检查无需
配置 API 路由白名单即可直连。同样原因，全局 X-Auth-Token 中间件对该
路径放行。

version 字段从版本单一来源 `app.version.get_version()` 读取（权威源
`.claude-plugin/plugin.json`），避免与硬编码字符串漂移。
"""
from fastapi import APIRouter

from app.version import get_version

router = APIRouter()


def _read_version() -> str:
    """委托给版本单一来源；保留此名以兼容既有调用方/测试。"""
    return get_version()


@router.get("/health")
async def health():
    return {"ok": True, "service": "cost-estimation", "version": _read_version()}
