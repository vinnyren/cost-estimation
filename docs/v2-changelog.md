# v2.x Changelog

> 软件造价系统 v2.x 变更清单，供 release notes / 升级评估使用。最新版本条目在最上方，v2.0 全量基线在下方。开发者向架构细节见 `dev-guide.md`。

## 概览

- 11 个 GAP 全部闭环（GAP-A 到 GAP-K）
- 7 个 QA fix（ISSUE-002 ~ ISSUE-007 + 2 个 review finding）
- **零 breaking change**，向后兼容 v1.x
- 3 张新表 + 3 个 alembic migration，自动 fallback 不阻塞老库

---

## v2.9（2026-05-20）— 多标准功能规模测量 + SSM-BK-202509

> 来源：用户提出在评估中支持三种国标功能规模测量方法（IFPUG / NESMA / COSMIC），并基于一份新的行业基准报告重建基准数据。
> 三份标准（GB/T 42449 / 42452 / 42588）均为功能规模测量标准，**成本流水线不变**，变的是"怎么数规模"。
> **零 breaking change**：旧 `fp_method` 字段迁移到 `measurement_method`；老项目默认 `nesma_estimated`；alembic migration `6fd4cb76f438` 新增 `measurement_method` + COSMIC 四列均为可空，老库自动 fallback。

### 多标准（Part A）

| # | 描述 |
|---|---|
| A1 | **`Project.measurement_method` 字段** —— 五取值：`ifpug` / `nesma_indicative` / `nesma_estimated` / `nesma_detailed` / `cosmic`；旧死字段 `fp_method` 被取代（`quick` → `nesma_estimated`） |
| A2 | **策略包 `server/app/core/sizing/`** —— `base.SizeMethod` 协议 + `ifpug.py` / `nesma.py`（三级）/ `cosmic.py`；`get_method()` 注册表 |
| A3 | **`function_points` 新增 COSMIC 列** —— `cosmic_entry/exit/read/write` 可空整数；后端 `_apply_sizing(method, data)` 取代 v2.8 的 `_apply_ifpug`，按方法重算行级 `ufp/us` |
| A4 | **forward / reverse 按方法分派** —— `services/calc.py` 读 `project.measurement_method` 取策略；COSMIC 项目 forward 计算前将各 `FpItem.us ÷ cfp_to_fp` 换算为 FP 当量再走同一生产率/费率链；reverse 单一规模模型不依赖 FP 列表，COSMIC 换算不适用 |
| A5/A6 | **Wizard / FpFormModal 方法选择 + 按方法切换录入区** —— 项目向导第 2 步加「功能规模测量方法」单选；FpFormModal 按方法 v-show 控制 DET/RET/FTR、复杂度提示或 4 类数据移动输入；COSMIC 录入实时汇总 CFP；跨录入模型切换（进/出 COSMIC）弹强警告并保留旧数据 |
| A8 | **AI 提取按方法分支** —— `commands/cost.md` 先读 `measurement_method`，COSMIC 走「功能过程 + 4 类数据移动」prompt，其他走「5 类 + DET/RET/FTR」prompt，写入时带方法对应字段 |
| A9 | **报告体现方法** —— `report_builder.py` 新增 `measurement_method` / `cfp_to_fp` 参数；评估报告书新增「三、评估方法」声明（写入方法标准全称）；COSMIC 项目额外追加 CFP→FP 当量换算备注 |

### 基准数据（Part B）

| # | 描述 |
|---|---|
| B1 | **SSM-BK-202509 重建基准数据** —— 新 `server/app/data/ssm_bk_202509.json`，覆盖全行业及 8 个分行业 P10–P90 生产率、维护型 / AI+开发生产率、缺陷密度、交付质量、工作量分布、功能点单价（1336 元）及 CF 表；`config.csbmk_seed_path` 切到新文件，`csbmk_202510.json` 保留不删 |
| B2 | **`cfp_to_fp` 换算系数** —— 全局参数新增 `cfp_to_fp`（默认 1.2，对应 1 NESMA-FP ≈ 1.2 CFP），COSMIC 项目走 `FP 当量 = CFP ÷ cfp_to_fp` 后接 FP/人月生产率，避免手工臆造 CFP 专属生产率表 |
| B3 | **README 标准更正** —— GB/T 42452 旧误标为「软件开发成本度量规范应用指南」，更正为「COSMIC 功能规模测量方法」；标准合规章节补 42449 / 42588；顶部基准从 CSBMK®-202510 同步为 SSM-BK-202509 |

### 测试基线（v2.9）

- Backend pytest: **360 / 360**（含 `test_v2_9_*` 系列新增测试：sizing 各策略 / forward COSMIC 换算 / 报告方法声明 / SSM-BK 数值校验）
- Frontend vitest: **335 / 335**（含 `FpFormModal-methods.test` / `ProjectWizard-steps.test` 方法切换覆盖）
- vue-tsc + vite build: clean

### 升级（v2.6 → v2.9）

```bash
git pull
cd server && .venv/bin/alembic upgrade head   # 6fd4cb76f438: measurement_method + cosmic 列
```

> 老项目首次进编辑或计算时 `measurement_method` 默认 `nesma_estimated`，行为与 v2.8 NESMA 估算一致；切到 IFPUG 详细 / COSMIC 需在「编辑设定」里改方法并按新录入模型补字段。

---

## v2.8（2026-05-19）— 42449 算法 / 基准对齐 / 全局参数编辑 / 反算补全

> Phase A / B / C / D 四块同期完成。pytest 289 / vitest 308 / vue-tsc / build 全绿。

| 阶段 | 描述 |
|---|---|
| A · IFPUG 算法 | `core/ifpug.py` 复杂度查表（DET/RET/FTR → 复杂度 → UFP），FP 表加 `det/ret/ftr` 列，`Project.assessment_kind`（development / enhancement）覆盖 DFP / EFP 口径；FpFormModal IFPUG 联动；Wizard 第 2 步加「评估口径」单选 |
| B · 基准数据对齐 2025 PDF | `csbmk_202510.json` 6 处数值修正（修改类型 / 平台 / 支持 / 用户规模等）；补因子表 / 展示数据 / 附录 C；`ParamGlobal.reseed_if_outdated()` 旧库刷新到新 seed（用户改过的项保留） |
| C · 全局参数草稿编辑 | ParamManager 全局模式三按钮：**保存 / 撤销 / 还原出厂**；草稿在缓冲区累积不即时落库；顶部状态条「● 有未保存的修改 / 参数已是最新保存状态」 |
| D · 反算补全 | reverse 项目结果页新增三级模块树（build_module_tree 逐层分摊）；「按反算补全 FP」按钮触发 `reverse_fill` AI 任务，按反算分摊量级回写 FP 表 |
| 选档 | 结果页三档卡片可点选 P10/P50/P90 → 持久化到 `Project.selected_band`；Excel 报告按选档导出 |

### 升级（v2.7 → v2.8）

```bash
git pull
cd server && .venv/bin/alembic upgrade head   # IFPUG/assessment_kind/selected_band 列
```

---

## v2.7（2026-05-18）— 预留入口补全

> 补全 v2.6 遗留的三个 stub 入口。pytest 233 / vitest 296 / vue-tsc 0 / build OK。

| 入口 | 描述 |
|---|---|
| 全局审计聚合 | `GET /api/audit` 跨项目时间线 + AuditView global 分支 + 项目徽章；侧边栏「审计日志」从规划中状态变为实装 |
| 批量导出 / 导入 | `POST /api/projects/export` / `import` JSON bundle；ProjectList 复选框选择 + 批量导出 / 导入按钮启用；导入带规模上限校验，旧 bundle 兼容 |
| 采纳 FP | AiTaskPanel 完成后新增「采纳 FP」按钮 → `POST /api/projects/{id}/functions/accept-drafts`，把 `claude_draft` 升级为 `ai_extracted` 并自动留快照 |

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
