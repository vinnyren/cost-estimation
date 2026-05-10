# Mutation Testing Report（首次基线）

**日期**：2026-05-10
**目标范围**：`server/app/core/{forward.py, reverse.py, allocator.py, factors.py, context.py}`
**目标杀死率**：≥ 70%（spec §11，目标，非硬要求）
**工具**：`mutmut 3.5.0`
**测试 runner**：`pytest -x -q`（限定 `tests/unit/test_{forward,reverse,allocator,factors,context,models}.py`）

---

## 当前状态：mutant 已生成 + 测试套件已关联，但本地无法获取存活/杀死分类

mutmut **已成功生成 176 个 mutants**（覆盖 4 个核心算法模块），并在 stats 阶段
**正确把每个 mutated 函数关联到单元测试**（参见 `server/mutants/mutmut-stats.json`）。
但在 mutation testing 阶段，所有 176 个 mutants 都被 mutmut 标记为 `segfault` —
即 fork() 出来的子进程在 pytest 启动前后崩溃，mutmut 拿不到 exit code，导致全部判定为
"💥 segfault"，无法区分 killed / survived。

这不是项目代码或测试的问题：手动跑同一个 mutant 时 pytest 正常退出（killed = exit 1）：

```bash
cd server/mutants
MUTANT_UNDER_TEST=app.core.forward.x_calculate_forward__mutmut_1 \
  ../.venv/bin/python -m pytest -x -q tests/unit/test_forward.py
# → 1 failed (TypeError: NoneType * float)，等价于 mutant 被 killed
```

### 根因

mutmut v3 的 `_run` 在 `os.fork()` 后的子进程内 **inproc** 调 `pytest.main(...)`。
当 site-packages 含 SQLAlchemy / FastAPI / pdfplumber / python-magic 等带 C 扩展或
全局状态的库时，macOS Darwin 25.4.0 + Python 3.11.15 + fork() 组合会触发 SIGSEGV。
这是 mutmut v3 已知的 macOS 兼容性问题，社区相关讨论：
- mutmut GitHub issues：fork() 与 SQLAlchemy/FastAPI 全局 state 冲突
- macOS `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` 不能解决 Python 层 SIGSEGV

已尝试的缓解措施（**均未解决**）：
1. `--max-children 1`（去掉并发）→ 仍全 segfault
2. `tests_dir` 缩到 6 个 unit 测试文件（避开 integration）→ 仍全 segfault
3. `tests/conftest.py` 中 `from app.main import create_app` 改为 lazy import
   （避免 fork 时携带 SQLAlchemy/FastAPI 全局 state）→ 仍全 segfault

### 推论

问题位于 mutmut 自身或 fork 后 Python interpreter 的 C 扩展初始化阶段。本地难以完全
规避。下一步建议在 **CI（Linux runner）** 上跑 — Linux 的 fork + Python 没有 macOS 的
Objective-C 运行时初始化路径冲突，mutmut v3 在 Linux 跑通的报告普遍正面。

---

## mutmut 输出（本地）

```text
$ mutmut run
    done in 128ms (5 files mutated, 1 ignored, 0 unmodified)   ← Generating mutants
    done                                                        ← Running stats（关联测试 OK）
    done                                                        ← Running clean tests（基线绿）
    done                                                        ← Running forced fail（基线 OK）
Running mutation testing
    176/176  🎉 0 🫥 0  ⏰ 0  🤔 0  🙁 0  🔇 0  🧙 0
533.10 mutations/second

$ mutmut results | awk -F: '{print $NF}' | sort | uniq -c
   176  segfault
```

**注意**：`Running clean tests` 和 `Running forced fail` 两阶段都通过 — 说明 mutmut
**能在 mutants/ 子目录下正确驱动 pytest 子进程**（这两阶段不 fork 太多次）。崩溃只发生
在 mutation 阶段批量 fork 时。

## Mutant 分布

| 模块 | mutants | 行数 |
|---|---|---|
| `forward.py` | 45 | 55 |
| `reverse.py` | 58 | 72 |
| `allocator.py` | 46 | 42 |
| `factors.py` | 27 | 21 |
| `context.py` | 0 | 38 |
| **合计** | **176** | **228** |

> `context.py` 没有 mutant，因为它主要是 `@dataclass(frozen=True)` 与查表方法，
> mutmut 默认不变异 dataclass 字段与简单字典 lookup。

## 杀死率（占位）

由于本地 segfault，未能得出 killed/survived 数字。在 CI 上跑通后将更新此节：

- killed: TBD
- survived: TBD
- 杀死率：TBD %（目标 ≥ 70%）

## 值得关注的 mutant 样本（5 条，源自 `mutmut show`）

这些 mutant 已生成，但本地无法执行验证。在 CI 跑出实际结果前，先列出代表性样例供后续
审查时优先关注：

| Mutant ID | 文件:行 | 类型 | 解释 |
|---|---|---|---|
| `app.core.allocator.x_allocate__mutmut_5` | allocator.py:3 | 表达式置换为 None | `s_free = inp.target_us - s_locked` → `s_free = None`（应被 `if s_free <= 0` 立刻触发，预期 killed） |
| `app.core.factors.x_non_func_factor__mutmut_3` | factors.py:3 | 字面量变异 | 校验集合 `(-1, 0, 1)` → `(-2, 0, 1)`，仅在 `x == -1` 输入时引发 ValueError 差异（已有 `test_non_func_factor_min` 覆盖） |
| `app.core.reverse.x_calculate_reverse__mutmut_10` | reverse.py:8 | 算术运算变异 | `budget_ops = fp_budget * (1.0 - inp.alpha_dev)` → `(1.0 + inp.alpha_dev)`，会破坏预算守恒（test_reverse_with_ops_split 应能 catch） |
| `app.core.forward.x_calculate_forward__mutmut_1` | forward.py:2 | 表达式置换为 None | `us = sum(...)` → `us = None`，下游 `s = us * cf` 必然 TypeError（killed） |
| `app.core.factors.x_non_func_factor__mutmut_13` | factors.py:5 | 数值变异 | `+ 1.0` → 变体常量，会改变 baseline factor，由 `test_non_func_factor_baseline` catch |

## 已知 false-positives / 跳过

- `mutmut` 默认忽略 `__init__.py` 与 `__pycache__/`（已在 `[tool.mutmut].do_not_mutate` 显式声明）。
- `tests_dir` 显式列了 6 个 unit 测试文件，避开 `tests/integration/` 与 `tests/golden/` —
  后者依赖 repo-root 路径（如 `app/data/csbmk_202510.json`、`templates/report-v1.xlsx`）；
  mutmut v3 在 `server/mutants/` cwd 下跑测试时这些路径解析失败。
- `tests/property/test_roundtrip.py`（hypothesis）也被排除，因 hypothesis fork 行为
  本身就和 mutmut fork 不兼容（已是 mutmut 文档中记载的 known issue）。

## 维护

```bash
# 重新运行（Linux/CI 上跑通的概率较高）：
cd server && bash scripts/run_mutmut.sh

# 查看具体 mutant 内容：
cd server && ./.venv/bin/mutmut show <mutant-id>

# 仅查看某模块的 mutant：
cd server && ./.venv/bin/mutmut results | grep app.core.forward
```

## 后续行动（TODO）

1. **CI 上跑 mutmut** — 在 Plan 5 / CI 接入时新增 GitHub Actions job（Linux runner）
   跑 `bash server/scripts/run_mutmut.sh`，把 killed/survived 数字与杀死率追加到本报告。
2. **如果 CI 上仍 segfault**，考虑：
   - 切到 `cosmic-ray` 或 `mutpy` 替代 mutmut v3
   - 降级到 `mutmut==2.x`（v2 用 subprocess 而非 fork，但配置语法不同，需要重写
     `[tool.mutmut]` 段）
3. **杀死率达标后**（CI 给出 ≥ 70% 数字），把本报告"占位"段落替换为实际数据 +
   5–10 条 survived mutant 的具体修复建议。
4. **若杀死率 < 70%**：survived mutant 通常意味着测试缺失边界 case（off-by-one、
   零/负值、空集合）— 在 `tests/unit/test_*.py` 中按模块补齐。
