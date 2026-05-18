"""Pydantic schemas for the audit-log surface (v2.0 GAP-J, Task T5)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditOut(BaseModel):
    id: int                  # 单调递增主键，同时作 cursor pagination 的游标
    project_id: str          # 关联 Project.id；项目删除时同步级联清理
    ts: datetime             # 写入时间戳（服务端 UTC）
    actor: str | None        # v3 引入用户体系后回填；v2.0 阶段恒为 None
    # action 取值清单（middleware/audit.py 维护）：
    #   create | update | delete | calc | export | restore | snapshot
    action: str
    target: str | None       # 操作对象（如导出文件名、被恢复的快照 id 等）
    diff_json: str | None    # 变更详情的 JSON 字符串；create/delete 等可为 None

    model_config = ConfigDict(from_attributes=True)


class AuditGlobalOut(BaseModel):
    """全局审计条目 — 在 AuditOut 字段基础上附带项目名（跨项目时间线用）。"""

    id: int
    project_id: str
    project_name: str
    ts: datetime
    actor: str | None
    action: str
    target: str | None
    diff_json: str | None
