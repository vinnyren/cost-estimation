"""安装前置检查：Python 版本、libmagic、pip 镜像。"""
from __future__ import annotations

import ctypes.util
import sys
import urllib.error
import urllib.request
from typing import Optional

import click

MIN_PYTHON = (3, 11)
PIP_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple/"
PIP_MIRROR_TIMEOUT = 5.0


def _find_libmagic() -> Optional[str]:
    return ctypes.util.find_library("magic")


def _probe_url(url: str, timeout: float) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except (urllib.error.URLError, OSError):
        return False


@click.command()
def cli() -> None:
    """运行安装前置检查。"""
    failed = False

    # 1. Python 版本
    cur = sys.version_info[:2]
    if cur < MIN_PYTHON:
        click.echo(
            f"✗ Python 版本过低: {cur[0]}.{cur[1]} < 3.11",
            err=True,
        )
        failed = True
    else:
        click.echo(f"✓ Python {cur[0]}.{cur[1]}")

    # 2. libmagic
    lib = _find_libmagic()
    if lib is None:
        click.echo(
            "✗ 未找到 libmagic："
            "macOS 用 `brew install libmagic`；"
            "Ubuntu/Debian 用 `apt install libmagic1`；"
            "RHEL/CentOS 用 `yum install file-libs`",
            err=True,
        )
        failed = True
    else:
        click.echo(f"✓ libmagic: {lib}")

    # 3. pip 镜像可达性（可选，仅 warning）
    if _probe_url(PIP_MIRROR, PIP_MIRROR_TIMEOUT):
        click.echo(f"✓ pip 镜像可达: {PIP_MIRROR}")
    else:
        click.echo(
            f"⚠ pip 镜像不可达: {PIP_MIRROR}（将回退默认源；如安装慢请检查网络）",
        )

    if failed:
        sys.exit(1)
    click.echo("✓ Preflight 全部通过。")


if __name__ == "__main__":
    cli()
