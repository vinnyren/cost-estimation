# 软件造价制作系统

基于 GB/T 36964 / T/CCUA 005-2024 / GB/T 28827.7-2022 / GB/T 42449-2023 / GB/T 42452-2023 / GB/T 42588-2023 与 SSM-BK-202509 数据集的软件造价评估工具，作为 Claude Code Plugin 发布。

> 当前版本 **v2.6.0** · 数据基准 SSM-BK-202509 · 完整变更见 [docs/v2-changelog.md](docs/v2-changelog.md)

## 功能

- **正向模式**（功能点 → 成本）：上传需求文档 → AI 提取功能点 → P10/P50/P90 三档成本估算。
- **反向模式**（目标成本 → 功能点）：输入万元目标造价 → 单一规模模型反推三档功能点规模 → 按现有 FP 各一级模块占比把 UFP 细化分摊到模块。
- **NESMA 估算法**：EI/EO/EQ/ILF/EIF 五类别、低/中/高复杂度。
- **6 行业 + 37 城**生产率与费率，CSBMK®-202510 内置。
- **17+ 调整因子全部可配**：开发因子 5 项 + 运维因子 11 项 + CF 阶段因子，含中文说明与悬停帮助。
- **AI 提取功能点**：上传文档后在「AI 任务面板」一键发起，后台调 Claude Code 读文档生成 NESMA FP 草稿；也可在终端运行 `/cost-estimation:cost <project_id>`。
- **功能点编辑**：模块树过滤、增删改查、历史版本快照与恢复。
- **创建项目向导**：客户/评估方 + 项目类型 + 阶段 + 城市/行业 + 评估方式 + 因子选择 + 实时 CF 预览，项目设定可二次编辑。
- **参数管理**：项目级 override + 全局参数库、参数快照、项目复制、审计日志。
- **Excel 报告**：6-sheet 行业评估表（封面 / 评估结果汇总 / 模块功能点及费用分项统计表 / 系统功能点明细表 / 评估报告书 / 调整因子表），按项目模式导出，反向项目报告总费用 = 目标造价。
- **大文件上传**：支持 PDF/Word/Excel/MD/TXT，单文件最大 500MB，分块流式写盘。
- **本地隔离**：只绑 127.0.0.1，token + Origin + CORS 三层防护。

## 一键安装

```bash
# 在 Claude Code 中：
/plugin marketplace add github.com/vinnyren/cost-estimation
/plugin install cost-estimation
/cost-estimation:setup        # 首次：建后端 venv + 装依赖
/cost-estimation:cost         # 无参：启动后端 + 打开浏览器
```

启动后在浏览器创建项目、上传文档；回到终端运行 `/cost-estimation:cost <project_id>` 让 AI 提取功能点。详细操作见 [docs/user-guide.md](docs/user-guide.md)。

## 目录结构

```
.
├── .claude-plugin/         # Plugin 元信息（marketplace.json + plugin.json）
├── commands/               # slash 命令（setup / cost / cost-allocate / cost-stop）
├── reference/              # NESMA 规则 + CSBMK 说明
├── server/                 # FastAPI 后端 + 计算引擎
│   ├── app/
│   │   ├── core/           # 算法核心（forward / reverse / allocator）
│   │   ├── api/            # REST 路由
│   │   ├── parsers/        # PDF / Word / Excel 解析 + 上传校验
│   │   ├── exporters/      # Excel 报告生成（report_builder）
│   │   └── data/           # csbmk_202510.json + 因子中文 meta
│   └── tests/              # pytest（单元 + 集成 + 属性 + 黄金）
├── web/                    # Vue 3 前端 + Vitest + Playwright E2E
├── docs/
│   ├── user-guide.md       # 用户使用手册
│   ├── dev-guide.md        # 开发者指南
│   ├── troubleshooting.md  # 故障排查
│   └── v2-changelog.md     # 版本变更清单
└── SKILL.md                # AI 提取触发与规则
```

## 开发

```bash
# 后端
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest --cov=app

# 前端
cd web
npm install
npm run test          # vitest
npm run build         # vue-tsc 类型检查 + vite 构建
npm run dev           # 开发服务器（vite proxy 后端 8788）
npm run test:e2e      # Playwright E2E
```

详见 [docs/dev-guide.md](docs/dev-guide.md)。

## 覆盖率验证

项目维护 `coverage-baseline.json` 防止覆盖率退化：

```bash
./scripts/check-coverage.sh             # 跑全套测试 + 与 baseline 比对（>0.5% 退化退出 1）
./scripts/update-coverage-baseline.sh   # 覆盖率上升时锁定新 baseline
```

测试基线（v2.6）：

| 项 | 数量 |
|---|---:|
| Backend pytest | 218 |
| Frontend vitest | 282（1 skipped） |
| Playwright e2e | 28+ |
| Backend / Frontend coverage | 92%+ / line 96%+ |

## 文档

- [用户使用手册](docs/user-guide.md) —— 面向最终用户的逐页操作说明。
- [开发者指南](docs/dev-guide.md) —— 架构、API、计算引擎。
- [故障排查](docs/troubleshooting.md) —— 常见问题。
- [版本变更清单](docs/v2-changelog.md) —— v2.0 至 v2.6 全量变更。

## 标准合规

- GB/T 36964-2018 软件工程 软件开发成本度量规范
- T/CCUA 005-2024 软件研发成本度量规范实施指南
- GB/T 28827.7-2022 信息技术服务 运行维护 第 7 部分：成本度量规范
- GB/T 42449-2023 系统与软件工程 功能规模测量 IFPUG 方法
- GB/T 42452-2023 系统与软件工程 功能规模测量 COSMIC 方法
- GB/T 42588-2023 系统与软件工程 功能规模测量 NESMA 方法
- SSM-BK-202509 中国软件行业基准数据 2025 年 09 月版

## License

MIT
