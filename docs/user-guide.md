# 用户手册

## 安装

### 前置条件

- macOS 11+ / Ubuntu 20.04+ / Windows 10+（WSL2）
- Python 3.11+
- libmagic
  - macOS: `brew install libmagic`
  - Ubuntu: `sudo apt-get install libmagic1`
  - RHEL/CentOS: `sudo yum install file-libs`
- Node.js 20+ + pnpm 9（仅开发模式需要）
- Claude Code 1.0+

### 步骤

```bash
# 1. 添加 marketplace
/plugin marketplace add github.com/your-org/cost-estimation

# 2. 安装 plugin（自动下载到 ~/.claude/plugins/cache/cost-estimation）
/plugin install cost-estimation

# 3. 首次初始化（建 venv + 装依赖 + 建库 + seed CSBMK）
/cost-estimation:setup
```

预期输出：

```
✓ Python 3.12.4
✓ libmagic: /opt/homebrew/lib/libmagic.dylib
✓ pip 镜像可达
✓ Preflight 全部通过。
（pip install 输出...）
✓ 已装载 CSBMK seed（版本 CSBMK®-202510）。
✓ 数据库初始化完成: ~/.claude/projects/cost-estimation/db/cost.sqlite
✓ 安装完成。运行 /cost 即可启动 Web 界面
```

## 日常使用

### 启动

```bash
/cost
```

预期：浏览器自动打开 `http://127.0.0.1:8788/?t=<token>`，进入项目列表页。

### 正向模式（功能点 → 成本）

1. 点"新建项目"，5 步向导：模式选 forward → 名称 → 城市 / 行业 → 阶段 → 确认
2. 在 FP 编辑屏：
   - 点"上传文档让 AI 写第一稿"，上传需求清单（PDF/Word/Excel）
   - AI 解析后自动写入功能点（每条带 `source=ai_extracted` 标记）
   - 在表格里微调（增删改）
3. 点"参数管理"可调整任一因子（覆盖项有"自定义"徽章高亮）
4. 点"计算 → 结果页"查看三档金额（P10 乐观 / P50 中位推荐 / P90 保守）
5. 点"下载 Excel 报告"获得 7-Sheet xlsx

### 反向模式（目标成本 → 功能点）

1. 新建项目时选 reverse 模式
2. 直接进入结果页，输入目标总造价 + 其他费用，点"反算"
3. 系统按 P10/P50/P90 三档生产率反推 FP 数
4. 采纳推荐档（P50 默认）后，可在 FP 编辑屏看到 `source=allocator` 的"预算倒推"行
5. AI 辅助分摊会把总 FP 拆到模块（在 FP 表格中可微调）
6. 计算 → 验证反算回去与目标金额误差 ≤ 1%
7. 下载 Excel（封面页含"反向模式"水印）

### 停止

```bash
/cost-estimation:cost-stop
```

## 数据位置

- 数据库：`~/.claude/projects/cost-estimation/db/cost.sqlite`
- 上传文件：`~/.claude/projects/cost-estimation/uploads/<project_id>/`
- Excel 导出：`~/.claude/projects/cost-estimation/exports/`
- 一次性 token：`~/.claude/projects/cost-estimation/.token`（启动时生成、停止时清除）

## 备份与导出

直接复制 `~/.claude/projects/cost-estimation/db/cost.sqlite` 即可备份所有数据。

## 卸载

```bash
/plugin uninstall cost-estimation
rm -rf ~/.claude/projects/cost-estimation
```

## 常见问题

见 [troubleshooting.md](troubleshooting.md)。
