# 造价算法完善 / 基准数据对齐 / 全局参数 UI / 反算补全 — 设计文档

> 日期：2026-05-18 · 版本目标：v2.8 · 状态：已确认，待写实施计划

## 背景

v2.7 后用户提出四项改进，依据两份新材料：

- `doc/GB-T 42449-2023.pdf` —— 国标《系统与软件工程 功能规模测量 IFPUG 方法》。
  调研确认：这是一份**功能点计数标准**（不是造价标准），规定 RET/DET/FTR →
  低/中/高复杂度 → FP 取值的查表规则，以及开发/增强项目的规模公式。
- `doc/《2025年中国软件行业基准数据》.pdf` —— CSBMK®-202510 基准数据，作为
  系统基准数据的权威来源。

四项改进合为一份 spec、四个 Part。实施计划会分阶段。

## 现状（调研结论）

- 当前 FP 仅存 `us`，无 IFPUG 复杂度查表，`forward.py` 只做 `Σus`，不区分
  开发/增强项目。
- `server/app/data/csbmk_202510.json` 与 2025 PDF：生产率/费率/CF 一致，但
  6 处调整因子数值有误、`app_type` 多一档、缺多张因子表与展示数据、缺附录 C。
- 全局参数后端可写（`PATCH /api/params/global`、`POST /api/params/global/reset`），
  但前端 `ParamManager.vue` 的 `patchOverride` 在全局模式 `if(!projectId) return`
  直接丢弃，且无保存/撤销/还原按钮。
- 反算（v2.7）已有「目标价 → 单一规模 → UFP 总量 → 按一级模块占比分摊」，
  但只分到一级模块，且只产出汇总表、不动 FP 表。

---

## Part A — 造价算法完善（GB/T 42449-2023）

### A1 IFPUG 复杂度查表

**数据模型**：`FunctionPoint` 增加三列（alembic migration，均可空，老数据兼容）：
- `det` —— 数据元素类型数（Data Element Types）
- `ret` —— 记录元素类型数（Record Element Types，数据功能 ILF/EIF 用）
- `ftr` —— 引用文件数（File Types Referenced，事务功能 EI/EO/EQ 用）

**新增 `server/app/core/ifpug.py`**：
- `classify_complexity(category, det, ret, ftr) -> "low"|"average"|"high"`
  - 数据功能（ILF/EIF）按 RET×DET 查 42449 表 1：RET 1 / 2-5 / >5；DET 1-19 / 20-50 / >50。
  - 事务功能 EI 查表 6、EO/EQ 查表 7：按 FTR×DET。
  - 信息不足（det/ret/ftr 缺）时默认 `average`。
- `fp_value(category, complexity) -> int` 按表 2/8：
  - ILF 低 7 / 中 10 / 高 15；EIF 低 5 / 中 7 / 高 10
  - EI 低 3 / 中 4 / 高 6；EO 低 4 / 中 5 / 高 7；EQ 低 3 / 中 4 / 高 6

**前端 `FpFormModal`**：填 category + DET + RET/FTR → 实时按 `ifpug` 算出
complexity 与 UFP（替代手填 UFP）。AI 提取的草稿仍可带值，进编辑表单时按
IFPUG 重算并显示。

### A2 增强项目口径

**数据模型**：
- `Project` 增加 `assessment_kind` 列：`development`（开发项目）/ `enhancement`
  （增强项目），默认 `development`。独立于现有 `project_type`（dev_only/...）。
- `FunctionPoint` 的变更类型字段对齐 42449：取值 `add`/`change`/`delete`/`convert`
  （对应 ADD/CHGA/DEL/CFP）。复用现有 `modify_type` 列，扩展其取值域；旧值
  `new` 迁移为 `add`。

**算法**（`forward.py`）：规模计算从「Σus」改为按变更类型分类汇总：
- 开发项目：`DFP = ADD + CFP`（ADD = add 类 us 之和，CFP = convert 类）
- 增强项目：`EFP = ADD + CHGA + CFP + DEL`（CHGA = change、DEL = delete）

**报告**：FP 计数声明输出 `<S> FP (IFPUG-GB/T 42449-2023)` 格式。

### A 测试
后端：`ifpug.classify_complexity` / `fp_value` 全分支单测；forward 开发/增强
两种口径单测。前端：FpFormModal 复杂度联动单测。

---

## Part B — 基准数据全量对齐 2025 PDF（含附录 C）

### B1 修正数值错误（影响算价）
重写 `server/app/data/csbmk_202510.json` 对齐 PDF：
- 修改类型因子：modify 0.70→0.80、remove 0.40→0.20；移除标准没有的 `convert 0.60`。
- 开发平台：C 类 1.5→1.2、PB/ASP 0.6→0.8。
- 更新频率：quarterly 0.95→0.78。
- 支持方式：remote 0.89→0.90、pure_onsite 1.08→1.20。
- 用户规模：≤1000 0.90→0.93、>10000 1.10→1.12。
- 系统关联性分档：1-5/6+ → 1-10/10+。
- 删除 `factors_dev.app_type` 中标准没有的「软件集成 1.20」档。

### B2 补齐缺表
- 因子表：吻合度因子（表 A.2，高 1/3 / 中 2/3 / 低 1）、软件类型因子（表 A.8，
  运维侧）、涉密因子（表 A.19）。
- 展示数据：缺陷密度/交付质量基准（表 4.4/4.5）、阶段工作量分布（表 4.6）、
  功能点单价（第 4.6 节）、运维费用占比补齐 P10-P90（现仅存 P50）。
- 附录 C 数据表：硬件运维单位工作量（表 C.1）、安全服务规模单价（表 C.2）。

### B3 库迁移
`csbmk_202510.json` 是 seed 源，已 seed 进 `ParamGlobal` 表的旧数据需对齐：
实现一次性 reset + re-seed 迁移（脚本或 bootstrap 逻辑），把库刷新为新 JSON。

### 范围边界（YAGNI）
附录 C **仅作数据表入库**，供后续取用。基于附录 C 的「硬件运维成本计算器」
是另一套成本模型，**本 spec 不实现**，需要时单独立项。

### B 测试
后端：JSON schema/数值校验测试（关键因子值与 PDF 对齐）、reset+re-seed
迁移后 `ParamGlobal` 值正确性测试。

---

## Part C — 全局参数保存 / 撤销 / 还原（ParamManager）

### C1 接通全局编辑
修 `ParamManager.vue` 的 `patchOverride`：全局模式（`projectId` 为 null）
不再直接 return，改为走 `PATCH /api/params/global`。

### C2 草稿态编辑 + 三按钮
全局模式下，费率 / 生产率 / 开发因子 / 运维因子 / 规模变更 五个参数 tab
改为**草稿态编辑**：改动写入本地缓冲，不即时落库。每个 tab 顶部加三个按钮：
- **保存** —— 批量把本页改动 `PATCH /api/params/global`（逐 leaf key）。
- **撤销** —— 丢弃未保存的缓冲改动，回到上次保存值。
- **还原出厂** —— 二次确认后调 `POST /api/params/global/reset`，重置为 CSBMK
  默认值；成功后重新拉取参数。
- 有未保存改动时给视觉提示（如按钮高亮 / 离开拦截）。

项目级参数页（`/projects/:id/parameters`）保持现有即时保存行为不变。

### C 测试
前端：全局模式草稿编辑 → 保存调 `patchGlobal`、撤销回滚、还原调 `reset`
的单测；项目模式即时保存不回归。

---

## Part D — 反算三级模块树细化 + AI 补全 FP

### D1 三级模块树分摊
`server/app/services/calc.py` 的 `_allocate_ufp_to_modules` 从「按一级模块
（subsystem, l1_module）一层分摊」改为**沿 子系统→一级→二级 模块树逐层分摊**：
- 读项目现有 FP，按三级 `(subsystem, l1_module, l2_module)` 建树。
- 目标 UFP 自上而下逐层按现有 UFP 占比分摊到每个节点。
- 输出树形结构 `module_allocation_tree`，每个节点含 `current_ufp` /
  `allocated_ufp` / `delta_ufp` / `ratio` / `children`。
- 现有 FP 表为空的叶子按均分或提示。

### D2 AI 补全 FP
反算后对每个叶子模块比较「分摊后 UFP vs 现有 UFP」：
- **缺口（delta > 0）** → 触发 AI 生成。新增 AI 任务类型 `reverse_fill`：
  - 给 AI 的输入：模块路径（子系统/一级/二级）、需补的目标 UFP、该模块现有
    FP（作风格参考）、项目已上传文档（若有，作语境）。
  - AI 产出：若干有名称、描述、类别、复杂度的功能点草稿，UFP 合计 ≈ 缺口。
  - 写入 FP 表，`source = "reverse_draft"`。
- **超出（delta < 0）** → 按比例下调该模块现有 FP 的 `us`。

走现有 AI 任务机制（`AiTask` 表 + 插件 spawn + 任务面板轮询）。`reverse_fill`
任务的 prompt 与现有 `extract` 不同，需新增对应命令/prompt 段。

### D3 前端
反算结果页「反算 UFP 模块细化分摊」表改为**树形展示**（与 FP 编辑页模块树
一致）。加「按反算补全 FP」按钮 → 触发 `reverse_fill` AI 任务 → 任务面板显示
进度 → 完成后刷新 FP 表。UI 明示：AI 生成的草稿是按模块语境的合理推测、
需人工审核（配合既有「采纳 FP」按钮转正）。

### D 测试
后端：三级树分摊（多层占比、空模块）、`reverse_fill` 任务创建与缺口计算
单测。前端：树形分摊表渲染、补全按钮触发 AI 任务单测。

---

## 不做的事（YAGNI）

- 附录 C 硬件运维成本计算器（仅入库数据，不建算法/UI）。
- 不改正向/反算的三档结构（仍 P10/P50/P90，不引入 P25/P75）。
- 项目级参数页不改即时保存行为。
- 反算补全只针对开发 FP；运维侧不在本 spec。

## 验收

- FP 编辑器填 DET/RET/FTR 自动按 42449 表得复杂度与 UFP；增强项目按
  EFP 公式计规模；报告带 IFPUG 计数声明。
- `csbmk_202510.json` 与 2025 PDF 全量一致（含附录 C 数据表），`ParamGlobal`
  库已对齐。
- 全局参数页可草稿编辑，保存/撤销/还原出厂三按钮可用。
- 反算结果页显示三级模块树分摊；「按反算补全 FP」触发 AI 生成有描述的功能点
  草稿写入 FP 表。
- pytest / vitest / vue-tsc / build 全绿；含 1 个 alembic migration（FP 加
  det/ret/ftr、modify_type 取值迁移、Project 加 assessment_kind）。
