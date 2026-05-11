# v2.0 Changelog

> 软件造价系统 v2.0 全量变更清单，供 release notes / 升级评估使用。开发者向架构细节见 `dev-guide.md` 的 "v2.0 架构新增" 章节。

## 概览

- 11 个 GAP 全部闭环（GAP-A 到 GAP-K）
- 7 个 QA fix（ISSUE-002 ~ ISSUE-007 + 2 个 review finding）
- **零 breaking change**，向后兼容 v1.x
- 3 张新表 + 3 个 alembic migration，自动 fallback 不阻塞老库

## GAP 闭环

| GAP | 描述 | 入口 |
|---|---|---|
| GAP-A | 主工作流命令骨架完善 | `commands/cost.md` |
| GAP-B | 项目复制（一键 clone 含 functions + factors_overrides） | `POST /api/projects/{id}/copy` / ProjectActionMenu |
| GAP-C | NESMA 提取 prompt 增强（识别率提升） | `SKILL.md` / FpEditor 的 AI hint |
| GAP-D | 项目级因子覆盖（per-project factors_dev/ops_json） | ProjectWizard 第 6 步 / FactorTable |
| GAP-E | 全局参数快照（CRUD + 一键回滚） | `/api/params/snapshots*` / ParamManager 快照 tab |
| GAP-F | 项目审计流水（PATCH/POST/PUT/DELETE 全记录） | `AuditMiddleware` / AuditView / `/projects/:id/audit` |
| GAP-G | 项目列表服务端搜索/筛选/分页（q/city/industry/phase/mode/sort/order/page/size） | ProjectList toolbar + meta envelope |
| GAP-H | 阶段分摊向导（allocator UI + 导出） | `commands/cost-allocate.md` / ResultView allocator panel |
| GAP-I | ParamManager 4 个 stub tab 全部实装（生产率 / 因子 / 阶段 / 规模变更） | ParamManager.vue |
| GAP-J | 阶段系数即时预览 + alpha 三档进度因子 | PhaseCfPreview / AlphaSlider |
| GAP-K | 全局参数 effective 视图（seed + 用户覆盖 + 快照合并） | `GET /api/params/effective` |

## QA / Review Fix

| ID | 描述 |
|---|---|
| ISSUE-002 | ParamManager 切换 tab 状态丢失 → Pinia store 改为 keep-alive |
| ISSUE-003 | 反向模式 BUDGET_NEGATIVE 错误码前端无引导 → 加 inline 错误 + 修正建议 |
| ISSUE-004 | 项目列表 N+1 查询（每行单独 query function_count） → 加 SUM 子查询 |
| ISSUE-005 | Excel 导出大项目（>500 FP 行）超时 → openpyxl write_only 模式 |
| ISSUE-006 | AuditView 翻页无 loading 态 → 加骨架屏 |
| ISSUE-007 | FactorTable 切换 dev/ops tab 滚动位置丢失 → 加 scroll-position memo |
| Review-1 | AuditMiddleware 写入失败应 fail-open（不阻塞业务）→ 加 try/except 包裹 |
| Review-2 | snapshots restore 缺事务边界 → 包 `with session.begin()` |

## Breaking Changes

**无。** v2.0 全部向后兼容：

- `GET /api/projects` 不带 query 时返回旧格式（裸数组），带任意新 query 时返回 envelope
- `projects` 表新增列 `factors_dev_json` / `factors_ops_json` 默认 NULL，老逻辑读全局 factors 兜底
- 新表 `param_snapshots` / `audit_log` 独立存在，删了不影响主链路
- core/ 层算法签名不变，golden 测试照常通过（489,180 元 ±100）

## 数据迁移

3 个 alembic migration，自动 fallback：

```bash
# 新装用户：bootstrap 一次性 create_all，无需 migrate
python -m app.bootstrap --db ... --seed ...

# 升级用户（v1.x → v2.0）：alembic upgrade
cd server && .venv/bin/alembic upgrade head
```

| Migration | 安全性 |
|---|---|
| `9b1c4f2e7a3d`（projects 加两列 JSON） | ADD COLUMN 默认 NULL，无锁、毫秒级 |
| `a4d8e6c2b9f1`（param_snapshots 新表） | CREATE TABLE，纯加法 |
| `b7e2f1d9c4a8`（audit_log 新表） | CREATE TABLE，纯加法 |

> 如果 dev DB 通过 `Base.metadata.create_all` 已经建过新列再跑 migration 会报 duplicate column，`alembic stamp head` 跳过即可（详见 `troubleshooting.md`）。

## 依赖变更

- **移除** `element-plus`（前端 bundle gzipped -85%，180KB → 27KB）
- **保留** 后端全部 v1.x 依赖（FastAPI / SQLAlchemy / openpyxl 等版本不变）

## 升级建议

1. 备份 SQLite：`cp ~/.claude/projects/cost-estimation/db/cost.sqlite{,.v1.bak}`
2. 升级 plugin：`/plugin install cost-estimation@v2.0.0`
3. 跑 migration：`cd server && .venv/bin/alembic upgrade head`
4. 验证：打开 ProjectList，确认筛选 / 分页 / 复制按钮可用

> 升级失败回滚：直接还原 `.sqlite.v1.bak`，重装 v1.x plugin。
