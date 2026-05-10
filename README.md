# 软件造价制作系统

基于 GB/T 36964 / T/CCUA 005-2024 / GB/T 28827.7-2022 / GB/T 42452-2023 与 CSBMK®-202510 数据集的软件造价评估工具，作为 Claude Code Plugin 发布。

## 功能

- ✅ **正向模式**（功能点 → 成本）：上传需求文档 → AI 提取 FP → 三档成本估算
- ✅ **反向模式**（目标成本 → 功能点）：输入预算 → 反推三档 FP → AI 分摊到模块
- ✅ **NESMA 估算法**（默认）：EI/EO/EQ/ILF/EIF 5 类、低中高复杂度
- ✅ **6 行业 + 37 城**生产率与费率（CSBMK®-202510 内置）
- ✅ **17+ 调整因子**：开发因子 5 项 + 运维因子 11 项 + CF 阶段因子
- ✅ **Excel 报告**：7 Sheet 模板（封面 / 摘要 / 报告书 / 调整因子 / FP 表 / 详细计算 / 参数附录）
- ✅ **本地隔离**：只绑 127.0.0.1，token + Origin + CORS 三层防护

## 一键安装

```bash
# 在 Claude Code 中：
/plugin marketplace add github.com/your-org/cost-estimation
/plugin install cost-estimation
/cost-estimation:setup
/cost
```

详见 [docs/user-guide.md](docs/user-guide.md)。

## 目录结构

```
.
├── .claude-plugin/         # Plugin 元信息（marketplace.json + plugin.json）
├── commands/               # slash 命令（setup / cost / cost-stop）
├── reference/              # NESMA 规则 + CSBMK 说明
├── server/                 # FastAPI 后端 + 计算引擎
│   ├── app/
│   │   ├── core/           # 算法核心（forward / reverse / allocator）
│   │   ├── api/            # REST 路由
│   │   ├── parsers/        # PDF / Word / Excel 解析
│   │   ├── exporters/      # Excel 渲染
│   │   └── data/csbmk_202510.json
│   └── tests/              # pytest（单元 + 集成 + 黄金）
├── web/                    # Vue 3 前端 + Vitest + Playwright E2E
├── docs/
│   ├── user-guide.md       # 用户手册
│   ├── dev-guide.md        # 开发者指南
│   ├── troubleshooting.md  # 故障排查
│   ├── mutation-report.md  # 变异测试报告
│   └── superpowers/        # 设计与实施计划存档
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
pnpm install
pnpm test
pnpm dev      # 开发服务器（vite proxy 后端 8788）

# E2E
pnpm test:e2e
```

详见 [docs/dev-guide.md](docs/dev-guide.md)。

## 标准合规

- GB/T 36964-2018 软件工程 软件开发成本度量规范
- T/CCUA 005-2024 软件研发成本度量规范实施指南
- GB/T 28827.7-2022 信息技术服务 运行维护 第 7 部分：成本度量规范
- GB/T 42452-2023 软件工程 软件开发成本度量规范 应用指南
- CSBMK®-202510 中国软件行业基准数据 2025 年 10 月版

## License

MIT
