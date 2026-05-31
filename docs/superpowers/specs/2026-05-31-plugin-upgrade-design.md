# 插件升级功能设计（/cost-upgrade）

> 日期：2026-05-31
> 状态：设计已与用户分节确认，待 spec 复核 → writing-plans
> 背景：插件目前只有 `/setup`（首装）/ `/cost`（启动）/ `/cost-stop`，**无升级路径**。
> 跨版本升级靠 changelog 记录的手动 `git pull` + `alembic upgrade head`，且基准标准切换
> （CSBMK®-202510 → SSM-BK-202509）对已存在 / `modified=True` 行不会自动发生——这正是
> 2026-05-31 手动修复现网 DB 时踩的坑。本特性把升级固化为一条可重复、可测试、有安全网的命令。

## 目标

新增独立命令 `/cost-upgrade`：当 marketplace 更新插件版本后，用户手动跑一次，安全地把既有数据目录推进到当前代码版本。一条命令完成：

1. **备份 DB + 版本检测**
2. **alembic 迁移到 head**（含 stamp 漂移修复）
3. **基准数据重灯**（标准变更时全量重置 + 导出旧改动；不变时 reseed 未改动行）
4. **刷新 venv 依赖 + 前端**

非目标：不替代 `/setup`（首装）；不做自动启动；不触碰按项目的 `param_override` 定制。

## 关键事实（设计依据，已实测）

- **启动时**（`main.py` lifespan）只做 `Base.metadata.create_all`（建缺失【表】，**不改已存在表的列**）+ `seed_from_csbmk()`（只补缺失键，**不切换标准、不迁移**）。
- **alembic 不自动运行**——既不在启动也不在 setup。
- **现网 DB stamp 漂移**：`alembic_version=4b7939b0712d`，但实际 schema 已是 head（`measurement_method` / `cosmic_*` / `selected_band` 列、`ai_tasks` / `audit_log` / `param_snapshots` 表全在）。盲跑 `alembic upgrade head` 会重放 stamp 之后 3 个迁移、对已存在列再 `ADD COLUMN` → **崩溃**。正确动作是 `alembic stamp head`。
- **基准标准切换**对 `params_global` 已存在 / `modified=True` 行不会自动发生；`reseed_if_outdated` 跳过 `modified=True`，而历史迁移常把整批行误标 `modified=True`（持旧标准值），导致计算静默用旧值。
- 真实的按项目定制存于独立 `param_override` 表。
- `requirements.txt` 用 `>=` 下限锁，升级时 venv 可能需刷新依赖。

## 架构与组件（方案 A：瘦命令 + Python 升级模块）

```
commands/cost-upgrade.md          薄壳：路径检测(复用 setup 逻辑) + venv + 停服 + 调 python -m app.upgrade + 前端
server/app/upgrade.py             新增：升级编排 CLI(click)，复用既有件
  ├─ 复用 bootstrap.reseed_if_outdated() / _flatten()
  ├─ 复用 config.settings (csbmk_seed_path, db_path)
  └─ 复用 alembic 程序化 API (alembic.command / alembic.config)
server/tests/integration/test_upgrade.py   新增：升级各分支回归
```

`app.upgrade` 对外只有一个入口 `cli(--db, --seed, --ts, [--yes])`，内部拆成可独立测试的纯函数：

| 函数 | 职责 | 依赖 |
|---|---|---|
| `detect_state(db, seed)` | 内省实际表/列 + 读 `alembic_version` + `params_global.basis_version` + seed 目标版本，返回 `{schema_at_head, stamp_rev, missing_cols, basis_db, basis_target, standard_changed}` | DB、seed JSON、Base.metadata |
| `backup_db(db, ts)` | WAL checkpoint + 时间戳备份 `cost.sqlite.pre-upgrade-<ts>.bak` | DB |
| `reconcile_schema(db)` | 内省驱动的漂移修复（见下） | alembic、inspector、Base.metadata |
| `reconcile_baseline(db, seed, ts, state)` | 标准变更→导出+全量重置；不变→reseed 未改动行 | params/bootstrap |

`<ts>` 时间戳由命令层 bash 注入（`--ts`），Python 侧不调 `Date.now`/`datetime.now`，保持可复现、可测试。

### 边界清晰性

- 命令层只懂"路径 / venv / 停服 / 传参 / 前端构建"。
- `upgrade.py` 只懂"如何安全地把一个旧 DB 推进到当前代码版本"。
- 每个 `reconcile_*` 函数输入输出明确、可单独测。

## 版本检测与 alembic 漂移修复

`detect_state` **全部基于内省，不信任 stamp**：

```
schema:   stamp_rev(可能漂移) + 内省实际表/列(inspector) + Base.metadata(=代码 head 期望)
baseline: params_global.basis_version 去重(排除 'user') + seed JSON.version
```

`reconcile_schema` **用"内省驱动"而非"重放迁移链"**，避开漂移崩溃：

```python
# 伪代码
def reconcile_schema(db):
    create_all(engine)                              # 1. 幂等补齐缺失【表】
    missing = desired_columns(Base.metadata) - actual_columns(inspector)
    if not missing:
        alembic_stamp("head")                       # 2a. schema 已到位，仅修正版本戳 ← 现网走这条
    else:
        for col in missing:                         # 2b. 仅可空/带默认的加列(SQLite 支持)
            execute(f"ALTER TABLE {col.table} ADD COLUMN {col.ddl}")
        alembic_stamp("head")
```

### 显式假设（约束）

本插件的迁移历来是**加性 schema 变更**（新表 / 可空新列 / 索引；changelog 明确"COSMIC 四列均为可空，老库自动 fallback"）。因此 reconcile 用 `create_all + 可空 ADD COLUMN + stamp head` 比重放链更稳。

**若未来出现非加性 DDL（删列/改类型/加约束）或需数据回填的迁移**，必须在 `upgrade.py` 为那个 revision 加显式 handler。此约束明文写入代码注释与本 spec，避免日后误用 `reconcile_schema` 处理它无法安全处理的迁移。

## 基准数据重灯（两条路径）

判定：
```
db_standards   = { basis_version 去重 | 行 where basis_version != 'user' }
standard_changed = (seed.version ∉ db_standards)
```

### 路径 1 — 标准变更（如 CSBMK®-202510 → SSM-BK-202509）

```
1. 导出所有 modified=True 行 → $DATA_DIR/exports/upgrade-modified-params-<ts>.json
2. DELETE FROM params_global          # 清空，含死键(旧命名空间孤儿)
3. 全量 seed 新 JSON                   # 全部 basis_version=target, modified=False
→ 结果 = 纯新标准，与全新安装一致；旧改动有据可查
```

### 路径 2 — 标准不变（同版本内 JSON 微调，或重复跑）

```
1. reseed_if_outdated()    # 删 modified=False 重插(刷新被调过的默认值)，保留 modified=True
→ 同标准下的真实全局编辑被尊重，不导出、不重置
```

### 导出文件格式

`$DATA_DIR/exports/upgrade-modified-params-<ts>.json`：

```json
{
  "exported_at": "2026-05-31T19:30:00",
  "from_standard": "CSBMK®-202510",
  "to_standard": "SSM-BK-202509",
  "count": 222,
  "modified_rows": [
    {"key": "city_rate.北京.dev", "value": 32198, "basis_version": "CSBMK®-202510"}
  ]
}
```

### 两条铁律

- 按项目的 `param_override` 表**两条路径都绝不触碰**。
- 路径 1 是破坏性的，但备份先行；命令层先打印检测摘要 + 待导出行数 + 导出路径再执行。策略已选定"全量重置 + 导出"，故不每次复问（`--yes` 用于完全非交互场景）。

## 执行顺序

**前置**：不对运行中后端持有的 DB 动手。命令层先查 `.pid`，存活则按 `cost-stop` 逻辑停掉 + 清残留；升级完**不自动重启**，提示用户跑 `/cost`。若连 venv 都没有 → 提示"先跑 `/setup`"（升级 ≠ 首装）。

```
命令层 cost-upgrade.md:
 1. 路径检测(复用 setup：CLAUDE_PLUGIN_ROOT → sort -V → 旧布局) + DATA_DIR
 2. 确保 venv(≥3.11) 并 pip install -r requirements        # 刷新依赖
 3. 停活后端 + 清失效残留(.pid/.token/.port)
 4. ts=$(date +%Y%m%dT%H%M%S) ; python -m app.upgrade --db … --seed … --ts $ts
 5. web/dist 缺失则构建(复用 setup step6)
 6. 打印总结 + "运行 /cost 启动"

app.upgrade.cli:
 a. detect_state → 打印升级计划(schema from→head, 标准 from→to, 待导出行数)
 b. backup_db (WAL checkpoint + 时间戳副本)   ← 安全网，先于任何写
 c. reconcile_schema (create_all + 加可空列 + stamp head)
 d. reconcile_baseline (路径1 重置+导出 / 路径2 reseed)
 e. 打印结果总结(各项 + backup 路径 + export 路径)
```

## 错误处理 / 回滚

- 备份**先于一切变更** → 真正的回滚单元是这份文件副本。
- 任一步抛错：**立即停**，**不自动回滚**（自动恢复会掩盖部分状态、本身有风险），打印：失败步骤 + 错误 + 精确恢复命令 `cp <backup> <db>`，非零退出。
- **幂等**：成功后重跑是 no-op（schema 已 head → stamp 幂等；标准未变 → 路径 2 reseed 不丢数据）。失败修好后重跑安全。
- SQLite DDL 多为非事务性，故以文件备份而非 DB 事务作为回滚保证。

## 测试策略

`server/tests/integration/test_upgrade.py`，pytest 集成，覆盖 ≥80%：

| 测试 | 验证 |
|---|---|
| `test_detect_diverged_stamp` | "schema 到位但 stamp 落后"被正确识别（`schema_at_head=True`, `stamp_rev` 落后） |
| `test_reconcile_schema_stamps_when_current` | 漂移 DB → `alembic_version=head`，无 DDL 报错，列完好 |
| `test_reconcile_schema_adds_missing_nullable_column` | 真缺可空列的老库 → 加列 + stamp head |
| `test_baseline_standard_changed_full_reset_and_export` | CSBMK→SSM：params_global 全 SSM、死键清除、导出文件含 modified 行与正确 from/to |
| `test_baseline_standard_unchanged_reseed_unmodified` | 同标准：`modified=True` 保留、`modified=False` 刷新、不产生导出文件 |
| `test_param_override_untouched` | 两条路径下按项目覆盖行都幸存 |
| `test_upgrade_idempotent` | 连跑两次，第二次 no-op、不丢数据、stamp 仍 head |
| `test_upgrade_backup_created` | 变更前备份文件已生成 |

## 涉及文件

| 文件 | 动作 |
|---|---|
| `server/app/upgrade.py` | 新增 |
| `commands/cost-upgrade.md` | 新增 |
| `.claude-plugin/plugin.json` | `commands` 数组加 `./commands/cost-upgrade.md` |
| `server/tests/integration/test_upgrade.py` | 新增 |
| `docs/v2-changelog.md` | 加条目 |
| `README.md` | 命令表 / 升级说明补 `/cost-upgrade` |

## 开放问题

- 无（设计已分节确认）。
