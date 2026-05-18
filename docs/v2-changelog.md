# v2.x Changelog

> 软件造价系统 v2.x 变更清单，供 release notes / 升级评估使用。最新版本条目在最上方，v2.0 全量基线在下方。开发者向架构细节见 `dev-guide.md`。

## 概览

- 11 个 GAP 全部闭环（GAP-A 到 GAP-K）
- 7 个 QA fix（ISSUE-002 ~ ISSUE-007 + 2 个 review finding）
- **零 breaking change**，向后兼容 v1.x
- 3 张新表 + 3 个 alembic migration，自动 fallback 不阻塞老库

---

## v2.6（2026-05-18）— 反算重做与报告升级

> 来源：v2.5 release 后用户反馈，聚焦反算模型一致性、行业评估报告格式与大文件上传。**零 breaking change，无新表，无需 alembic migration。**

### 反算

| # | 描述 |
|---|---|
| 1 | **单一规模模型** — 旧反算把目标造价按 α 拆成开发/运维两份、各自反推出两个不同规模，FP 表只能存一个，写回后正向计算总额对不上。新模型让开发与运维共用同一个功能点规模，对每档直接求规模使 `forward(规模)` 总成本 = 目标造价；`budget_for_dev` / `budget_for_ops` 变成按生产率/费率推导的成本拆分（输出，不再是 α 输入），α 开发占比不再参与反算 |
| 2 | **反算以 UFP 为核心 + 细化分摊到模块** — 反算算出可承载的 UFP 总量后，读取项目现有 FP 表，按各一级模块现有 UFP 占比把目标 UFP 细化分摊到模块，给出每个模块的「现有 UFP / 分摊后 UFP / 需细化增加的差额」；反算结果页新增「反算 UFP 模块细化分摊」表 |
| 8 | **反算结果进页面自动计算** — reverse 项目若已有目标造价，进结果页即自动反算，无需再手动点「反算」 |
| 11 | **AllocatorPanel 反算分摊基于真实 FP 模块** — 分摊面板的模块来自项目真实功能点的一级模块；「写回 FP 表」确认框会显示规模前后量级，剧烈缩放时强警告，避免无声冲掉 FP 设计稿 |

### 报告

| # | 描述 |
|---|---|
| 3 | **报告改为模式感知** — Excel 导出不再永远走正向计算；按项目 `mode` 分流，reverse 项目报告总费用 = 目标造价 |
| 4 | **Excel 报告重做为 6-sheet 行业评估表格式** — 封面 / 评估结果汇总（规模·工作量·成本·造价主表）/ 模块功能点及费用分项统计表 / 系统功能点明细表 / 评估报告书（六章文字叙述）/ 调整因子表；修复旧版「评估报告书」sheet 空白的问题 |

### 上传

| # | 描述 |
|---|---|
| 6 | **大文件上传上限 50MB → 500MB** — 改为 1MB 分块流式写盘，不再整文件读进内存，超限立即中止；上传超时放宽到 10 分钟；上传失败弹窗显示真实原因（如「文件超过 500MB」），不再只显示「status code 4xx」 |
| 10 | **上传后引导增加「AI 任务面板」入口** — 上传文档后提示用户可点右上角「AI 任务面板」一键发起 AI 提取任务，提示条内直接带「打开 AI 任务面板」按钮 |

### 其它

| # | 描述 |
|---|---|
| 5 | **目标造价单位改为万元** — 向导和反算输入页的「目标总造价 / 其他费用」标签改为「万元」，计算层内部仍按元运算（边界 ×10000 换算） |
| 7 | **编辑设定可改评估方式与项目类型** — 修复「编辑设定把项目改成反向后不生效」的问题（后端 PATCH schema 之前漏了 `mode` / `project_type` 字段） |
| 9 | **FP 规模标识中文化** — FP 编辑表、反算分摊、结果页里面向用户的「US」改为中文「规模」 |

### 升级（v2.5 → v2.6）

```bash
git pull
# 无破坏性 schema 改动，无新表，无需 alembic migration
```

> v2.6 不新增数据表，不改动既有列结构，老项目数据完全兼容。reverse 老项目首次进结果页会按新单一规模模型自动重算。

---

## GAP 闭环

| GAP | 描述 | 入口 |
|---|---|---|
| GAP-A | AI 提取功能点（NESMA 5 类别自动归类 + 复杂度判定） | `SKILL.md` prompt + `/cost` 命令 + FpEditor claude_draft 高亮 + 30s polling |
| GAP-B | 17+ 调整因子 UI（5 dev + 11 ops + scale_change） | `projects.factors_*_json` + ParamManager 4 个 stub tab 实装 + Wizard dropdown |
| GAP-C | AI 模块分摊（反向 → P50 FP → AI 切模块） | `/cost-allocate` 命令 + ResultView allocator panel + `POST /api/calc/allocate` |
| GAP-D | 运维费率 / 运维生产率 UI | ParamManager 城市费率加 ops 列 + 生产率新增 productivity_ops 表 |
| GAP-E | alpha_dev / include_ops 配置 | `components/AlphaSlider.vue` + Wizard step 2 联动 |
| GAP-F | 项目列表搜索 / 筛选 / 排序 / 分页 | `GET /api/projects` q/city/industry/phase/mode/sort/order/page/size + ProjectList toolbar |
| GAP-G | 客户 / 评估方填写 | Wizard step 1 可选字段，写入 Excel 报告封面 |
| GAP-H | 参数快照 + restore | `param_snapshots` 表 + 4 个 endpoint + ParamManager 快照 tab |
| GAP-I | 项目复制（含 FP + 参数 override） | `POST /api/projects/{id}/copy` + `ProjectActionMenu.vue` |
| GAP-J | 项目审计日志 | `audit_log` 表 + `AuditMiddleware` + `AuditView.vue` + `GET /api/projects/{id}/audit` |
| GAP-K | 阶段 CF 实时预览 | Wizard step 3 + `components/PhaseCfPreview.vue` |

## QA / Review Fix

| ID | 描述 | 严重度 |
|---|---|---|
| ISSUE-002 | `/health` endpoint 硬编码 `"version": "1.0.0"` — 改为读 pyproject | MEDIUM |
| ISSUE-003 | `project.copy` 副本 audit 时间线空白 — middleware 为副本写 `project.create` + `diff_json={"copied_from":...}` | MEDIUM |
| ISSUE-004 | ProjectList card 阶段字段显示英文 key（bidding）— 走 PHASES 映射为中文（招标） | LOW |
| ISSUE-005 | scale_change 无 CSBMK 数据 — 补 csbmk_202510.json + `_FLAT_TOP_KEYS` 加 scale_change | MEDIUM |
| ISSUE-006 | element-plus 死代码依赖 — 移除（vendor-element 921KB → 0KB, bundle -85%） | MEDIUM |
| ISSUE-007 | ParamManager scale_change tab 冗余 label（OverrideField 内部 label 与表头列重复） | LOW |
| Review #1 | AuditMiddleware streaming-response 假定不显式 — 加 in-line 警示注释 | INFO |
| Review #2 | audit_log 不记 query params（fp.restore?version=3 追不到版本）— 序列化 sub_path + query 到 diff_json | INFO |

## Breaking Changes

**无。** v2.0 全部向后兼容：

- `GET /api/projects` 不带任何 v2 query param 时仍返回新 envelope `{success, data, meta}`，前端调用方需要适配（已统一 `projectsApi.query()` 解包）
- `projects` 表新增 `factors_dev_json` / `factors_ops_json` 默认 NULL，calc.py 读到 NULL 走 fallback 1.0 + warning，不阻塞老项目计算
- 新表 `param_snapshots` / `audit_log` 独立存在，与 v1 数据流无耦合
- core/ 层 forward / reverse / allocator 算法签名不变，golden 测试照常通过（170/170）

## 数据迁移

3 个 alembic migration，自动 fallback：

```bash
# 新装用户：bootstrap 一次性 create_all，无需单独 migrate
python -m app.bootstrap --db ... --seed ...

# 升级用户（v1.x → v2.0）：alembic upgrade
cd server && .venv/bin/alembic upgrade head
```

| Migration | 影响 | 安全性 |
|---|---|---|
| `9b1c4f2e7a3d` projects 加 factors_dev_json / factors_ops_json | ADD COLUMN（SQLite batch_alter）| 默认 NULL，无锁，毫秒级 |
| `a4d8e6c2b9f1` param_snapshots 表 | CREATE TABLE | 纯加法，无影响 |
| `b7e2f1d9c4a8` audit_log 表 + 3 索引 | CREATE TABLE + INDEX | 纯加法，无影响 |

> 如果 dev DB 通过 `Base.metadata.create_all` 已经建过新表/列再跑 migration 会报 duplicate column —— `alembic stamp head` 跳过即可，详见 `troubleshooting.md`。

## 依赖变更

| 依赖 | v1.1 | v2.0 |
|---|---|---|
| element-plus | 2.7.6 (~1MB minified) | **移除**（源码 0 处使用，纯死代码加载） |
| 后端 (FastAPI/SQLAlchemy/openpyxl 等) | 保持不变 | 同 v1.1 |

**Bundle 影响：**
- `vendor-element-*.js`: 921 KB / 297 KB gzipped → **0**（chunk 完全消失）
- 总 dist gzipped: ~1MB → ~200 KB（**-85%**）
- `pnpm build` 时间: 1.83s → 0.46s

## 升级建议

1. 备份 SQLite：`cp ~/.claude/projects/cost-estimation/.data/cost.sqlite{,.v1.bak}`
2. 升级 plugin：从 Claude Code marketplace 装 v2.0.0
3. 跑 migration：`cd server && .venv/bin/alembic upgrade head`
4. 验证：打开 ProjectList，确认 toolbar 出现 + 创建一个项目走完 7 步 Wizard + 验证 Wizard step 5 因子 dropdown 渲染

> 升级失败回滚：直接还原 `.sqlite.v1.bak`，重装 v1.x plugin。所有 v2 表 / 列删了不影响 v1.x 数据完整性。

## 测试基线

- Backend pytest: **170 / 170** (was 140 in v1.1)
- Frontend vitest: **220 + 1 skip / 33 files** (was 124)
- Playwright e2e: **3 / 3** (含新增 v2-wizard-flow)
- type-check + lint: clean
- Build: 0.46s

## 相关文档

- `README.md` — 用户向 v2.0 章节
- `docs/user-guide.md` — 第 12 章 v2.0 新功能与迁移
- `docs/dev-guide.md` — v2.0 架构新增
- `docs/troubleshooting.md` — v2.0 已知问题
- `docs/superpowers/specs/2026-05-11-v2-gap-closure-design.md` — 设计规范
- `docs/superpowers/plans/2026-05-11-plan-5-v2-gap-closure.md` — 实施计划
