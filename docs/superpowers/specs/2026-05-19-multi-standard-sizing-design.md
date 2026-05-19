# 多标准功能规模测量 + SSM-BK-202509 基准数据 — 设计文档

> 日期：2026-05-19 · 版本目标：v2.9 · 状态：已确认，待写实施计划

## 背景

用户提出在评估计算中引入三种国标功能规模测量方法，由用户按项目选择，按对应算法评估；
同时基于一份新的行业基准报告重建基准数据。涉及四份材料：

- `doc/GB-T 42449-2023.pdf` —— IFPUG 功能规模测量方法（v2.8 已部分集成 `core/ifpug.py`）。
- `doc/GB-T 42588-2023.pdf` —— NESMA 功能规模测量方法（ISO/IEC 24570）。
- `doc/GB-T 42452-2023.pdf` —— **COSMIC** 功能规模测量方法（ISO/IEC 19761）。
  注：项目 README 旧把 42452 标注为「软件开发成本度量规范应用指南」是**错的**，需一并更正。
- `中国软件行业基准数据报告（SSM-BK-202509）.pdf` —— CSBSG 发布的行业基准数据，
  生效 2025-10-01，废止 SSM-BK-202409。

### 调研结论

- 三份标准都是**功能规模测量（FP/FSM 计数）**标准，不是成本标准。成本流水线
  （规模→生产率→工作量→费率→成本，走 GB/T 36964 + 基准数据）不变，变的是**怎么数规模**。
- IFPUG（42449）与 NESMA（42588）共用「5 类功能 ILF/EIF/EI/EO/EQ + DET/RET/FTR」
  录入模型，规模单位 FP，与现有 FP 编辑器兼容。
- COSMIC（42452）是**另一套模型**：每个功能过程数 4 类数据移动（入口 Entry /
  出口 Exit / 读 Read / 写 Write），规模单位 CFP。
- `Project.fp_method` 字段（`nesma_estimated`/`ifpug`/`quick`）当前存在但**未接入任何算法**，
  是死字段，本 spec 将其取代。
- 当前基准数据存于 `server/app/data/csbmk_202510.json`（CSBMK®-202510）。
  SSM-BK-202509 与之同属 CSBSG 发布体系，更新更晚。

### 设计决策（来自澄清）

1. 完整支持三种标准，含 COSMIC 数据移动录入模型。
2. NESMA 三个精度级别全部展开。
3. 已有 FP 数据时允许切换方法；同录入模型沿用数据，进/出 COSMIC 弹框警告、旧数据保留不参与计算。
4. SSM-BK-202509 基准数据并入本 spec 作为一个 Part。
5. COSMIC 不手工臆造 CFP 生产率表；用可配置换算系数 `1 NESMA-FP ≈ 1.2 CFP`，
   `FP当量 = CFP ÷ 系数`，FP 当量走与 IFPUG/NESMA 相同的 FP/人月生产率，报告备注此换算。

---

## Part A — 多标准功能规模测量框架

### A1 方法选择（项目级）

`Project` 新增 `measurement_method` 字段，取代死字段 `fp_method`。五个取值：

| 取值 | 标准 | 录入模型 | 规模单位 |
|---|---|---|---|
| `ifpug` | GB/T 42449 IFPUG | category + DET/RET/FTR | FP |
| `nesma_indicative` | GB/T 42588 NESMA 预估 | 仅 ILF/EIF 计数 | FP |
| `nesma_estimated` | GB/T 42588 NESMA 估算 | category（复杂度取「中」） | FP |
| `nesma_detailed` | GB/T 42588 NESMA 详细 | category + DET/RET/FTR | FP |
| `cosmic` | GB/T 42452 COSMIC | 功能过程 + 入口/出口/读/写 | CFP |

- 项目创建向导与编辑设定页提供选择（参照 v2.8 `assessment_kind` 字段的位置与样式）。
- 默认 `nesma_estimated`。
- alembic migration 加列；旧 `fp_method` 值迁移：`ifpug`→`ifpug`、`nesma_estimated`→
  `nesma_estimated`、`quick`→`nesma_estimated`。`fp_method` 列保留或删除由实施计划定
  （倾向删除——确认无其它读取方）。

### A2 策略包 `server/app/core/sizing/`

- `base.py` —— `SizeMethod` 协议（用 `typing.Protocol`）：
  - `compute_entry_size(entry: dict) -> float` —— 单个 FP / 功能过程的未调整规模。
  - `size_unit: str` —— `"FP"` 或 `"CFP"`。
  - `input_model: str` —— `"ifpug_style"`（category+DET/RET/FTR 系）或 `"cosmic"`。
- `ifpug.py` —— 复用 v2.8 `core/ifpug.py` 的 `classify_complexity` / `fp_value`。
- `nesma.py` —— NESMA 三级：
  - 详细级：按 DET/RET/FTR 查 42588 复杂度矩阵（与 IFPUG 详细级一致，附录 B 规范性赋值表）。
  - 估算级：每个功能按「平均/中」复杂度直接取 UFP，不需 DET/RET。
  - 预估级：仅数 ILF/EIF，`UFP = a×#ILF + b×#EIF`。常数 a/b 以 GB/T 42588 标准为准
    （NESMA 预估常用 35/15，实施时从标准取准）。
- `cosmic.py` —— 每个功能过程 `CFP = 入口 + 出口 + 读 + 写`，项目规模 = Σ。
  COSMIC 每个功能过程至少含一个入口与一个出口或写（42452 规则），信息不足按兜底处理。
- `__init__.py` —— `get_method(measurement_method: str) -> SizeMethod` 注册表。

### A3 FP 数据模型扩展

`function_points` 表新增可空列（沿用 v2.8「加可空列」模式，配 alembic migration）：

- `cosmic_entry` / `cosmic_exit` / `cosmic_read` / `cosmic_write` —— 整数，COSMIC 用。

每个 FP 行按项目 `measurement_method` 解释所需字段：

| 方法 | 用到的字段 |
|---|---|
| `ifpug` / `nesma_detailed` | `category`、`det`、`ret`、`ftr` |
| `nesma_estimated` | `category`（复杂度固定「中」） |
| `nesma_indicative` | `category`（仅 ILF/EIF 参与） |
| `cosmic` | `cosmic_entry/exit/read/write`（`category` 不参与） |

后端 FP 创建/编辑时按方法重算该行规模：把 v2.8 的 `_apply_ifpug(data)` 推广为
`_apply_sizing(method, data)` —— 按方法调对应策略算 `ufp`/`us`（COSMIC 算 CFP 写入 `ufp`/`us`）。

### A4 forward / reverse 计算接入

- `services/calc.py`：`run_forward` / `run_reverse` 按项目 `measurement_method` 取策略，
  对 FP 列表汇总总规模。
- **规模单位分流**：
  - IFPUG / NESMA 各级 → 产出 FP → 直接走 FP/人月生产率表。
  - COSMIC → 产出 CFP → 先按换算系数转 FP 当量（见 B2），再走同一 FP/人月生产率表。
- `assessment_kind`（开发 development / 增强 enhancement，DFP/EFP）各方法各有增强口径：
  IFPUG/NESMA 沿用 v2.8 的 ADD/CHGA/CFP/DEL 汇总；COSMIC 按 42452 §6.12「FUR 变更的功能规模计算」。
  各方法的增强口径由对应策略模块实现。
- 反算（reverse）：目标价 → 反推总规模 → 按方法单位换算（COSMIC 反推 CFP）。

### A5 前端 FP 编辑器按方法切换表单

`FpFormModal` 按项目 `measurement_method` 渲染不同输入区：

- `ifpug` / `nesma_detailed` —— 现有 DET/RET/FTR + 类别（v2.8 已实现）。
- `nesma_estimated` —— 仅选类别，复杂度固定显示「中」。
- `nesma_indicative` —— 仅选 ILF/EIF。
- `cosmic` —— 功能过程名 + 入口/出口/读/写四个计数输入，实时算 CFP。

方法切换行为：

- IFPUG ↔ NESMA 各级（同 `ifpug_style` 模型）—— FP 数据直接沿用，仅按新方法重算规模/复杂度。
- 进 / 出 `cosmic`（跨录入模型）—— 弹框二次确认并警告「录入模型不同，需重新录入」；
  确认后旧 FP 数据**保留**但不参与该方法计算（不删除）。

### A6 AI 提取按方法

`commands/cost.md`（extract 命令）按项目 `measurement_method` 分支：

- IFPUG / NESMA —— 提取 5 类功能 + DET/RET/FTR（现有逻辑）。
- COSMIC —— 提取功能过程 + 4 类数据移动计数。

新增对应 prompt 段；FP 草稿写入时带方法对应字段。

### A7 报告体现方法

报告的 FP 计数声明带方法名与标准号，扩展 v2.8 的 IFPUG 声明：

- IFPUG：`<S> FP (IFPUG-GB/T 42449-2023)`
- NESMA：`<S> FP (NESMA-GB/T 42588-2023, <级别>)`
- COSMIC：`<S> CFP (COSMIC-GB/T 42452-2023)`，并备注 CFP→FP 当量换算（见 B2）。

### A 测试

- `core/sizing/` 各策略全分支单测：IFPUG 复用 v2.8；NESMA 三级公式；COSMIC 数据移动求和与兜底。
- forward / reverse 按方法分派的集成测试（含 COSMIC 经换算的成本链）。
- 前端：FpFormModal 按方法切表单、方法切换警告弹框单测。

---

## Part B — SSM-BK-202509 行业基准数据

### B1 重建基准数据集

用 SSM-BK-202509 重建项目基准数据，覆盖报告全部章节（全行业生产率、分行业生产率 8 档、
维护型开发生产率、AI+开发生产率、缺陷密度，及报告其余章节——共 27 页，实施阶段用 Read
工具完整读取取数）。

- **取代关系**：SSM-BK-202509 作为新的权威基准数据集，重建为
  `server/app/data/ssm_bk_202509.json`，`csbmk_202510.json` 被取代。
  理由：维护两套并行全量基准数据负担翻倍；SSM-BK 与 CSBMK 同属 CSBSG 体系且更新更晚。
- 项目 `basis_data_ver` 字段值更新为 `SSM-BK-202509`。
- 沿用 v2.8 的 `reseed_if_outdated` 迁移机制刷新 `ParamGlobal`，用户改过（`modified=True`）
  的项保留。JSON `version` 字段带迁移戳触发判定。
- 配套更新 `csbmk_factors_meta.json` 等元数据文件中与基准版本相关的标识。

### B2 COSMIC CFP→FP 当量换算

SSM-BK-202509 是 FP 口径，无 COSMIC（CFP）专属生产率。COSMIC 不手工臆造 CFP 生产率表，
改用换算：

- 全局参数新增可配置换算系数 `cfp_to_fp`，默认值对应 `1 NESMA-FP ≈ 1.2 CFP`，
  即 `FP当量 = CFP ÷ 1.2`。
- COSMIC 项目：总 CFP → `÷ cfp_to_fp` 得 FP 当量 → 走与 IFPUG/NESMA 相同的 FP/人月生产率
  与全部下游因子。
- 换算系数可在全局参数页草稿编辑（v2.8 已支持保存/撤销/还原）。
- 报告对 COSMIC 项目**备注**：结果经 CFP→FP 当量换算（系数 `<值>`），因无直接 COSMIC
  生产率基准。

### B3 README 更正

更正 README 与相关文档中 GB/T 42452-2023 的错误标注（应为「COSMIC 功能规模测量方法」，
不是「软件开发成本度量规范应用指南」）；标准合规章节补 GB/T 42449 / 42588。

### B 测试

- SSM-BK-202509 数值校验测试：关键生产率值（全行业/分行业 P10–P90、缺陷密度等）对齐 PDF。
- reset + re-seed 迁移后 `ParamGlobal` 值正确性测试。
- `cfp_to_fp` 换算系数参与 COSMIC 成本链的测试。

---

## 数据流

```
项目选 measurement_method
  → FP 按该方法录入模型存储（function_points 行）
  → 后端按方法策略算每项规模（_apply_sizing）
  → forward/reverse 汇总总规模（FP 或 CFP）
  → 单位分流：FP 直接用；CFP ÷ cfp_to_fp 转 FP 当量
  → FP/人月生产率表（SSM-BK-202509）
  → 工作量 → 费率 → 成本（CF / 因子 / 三档 / 费率，对所有方法一致）
```

## 错误处理

- 录入数据与方法不匹配（如 COSMIC 项目某行缺数据移动列）→ 该行规模按信息不足兜底
  （记 0 并在 trace 标注），不崩溃。
- 切换到 `cosmic` 但已有 `ifpug_style` 数据 → 前端弹框警告 + 旧数据保留不计入。
- COSMIC 项目但 `cfp_to_fp` 未配置 → 用默认 1.2。
- IFPUG/NESMA 信息不足 → 沿用 v2.8 默认复杂度 average 的兜底。

## 不做的事（YAGNI）

- 不把「维护型 / AI+开发生产率」做成可选生产率计算模式 —— SSM-BK-202509 的这些表仅作
  数据入库，需要时单独立项。
- 不为 COSMIC 手工构造 CFP/人月生产率基准 —— 用换算系数（B2）。
- 不保留 CSBMK®-202510 与 SSM-BK-202509 并行的双基准数据集 —— SSM-BK 取代之。
- 不改成本流水线下游（CF / 调整因子 / 三档 P10/P50/P90 / 费率）结构。

## 验收

- 项目可在向导/设定中选 5 种测量方法之一；FP 编辑器按方法切换录入表单。
- IFPUG / NESMA 三级 / COSMIC 各按对应标准算法得规模；forward/reverse 据此评估。
- COSMIC 经 `cfp_to_fp` 换算进入 FP 成本流水线；报告带方法声明与换算备注。
- 方法切换：同模型沿用数据，进/出 COSMIC 弹框警告、旧数据保留。
- 基准数据从 SSM-BK-202509 重建，`ParamGlobal` 已对齐，用户改动项保留。
- README 关于 42452 的错误标注已更正。
- pytest / vitest / vue-tsc / build 全绿；含 alembic migration（`measurement_method`、
  COSMIC 数据移动列）。
