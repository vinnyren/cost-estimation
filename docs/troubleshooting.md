# 故障排查

## 安装阶段

### `python3: command not found`

→ macOS: `brew install python@3.11`
→ Ubuntu: `sudo apt-get install python3.11 python3.11-venv`

### `Preflight ✗ libmagic 未找到`

→ macOS: `brew install libmagic`
→ Ubuntu/Debian: `sudo apt-get install libmagic1`
→ RHEL/CentOS: `sudo yum install file-libs`

### `pip install` 慢 / 卡住

→ 系统已默认使用清华镜像；如仍慢，编辑 `~/.pip/pip.conf` 加：

```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
```

或临时 `pip install -i https://pypi.org/simple/ ...` 用官方源。

## 启动阶段

### `8788–8800 端口全部占用`

→ 用 `lsof -nP -iTCP:8788 -sTCP:LISTEN` 查谁在占用，按需停掉，再重跑 `/cost`。

### 浏览器打开后 401 Unauthorized

→ 确保 URL 含 `?t=<token>`（`/cost` 命令会自动拼接）。手动构造 URL 时去 `~/.claude/projects/cost-estimation/.token` 读 token。
→ 如果服务进程没设置 `COST_AUTH_TOKEN` 环境变量，所有请求都会被中间件拒绝；重启服务并确认环境变量传入。

### `/cost-stop` 后再次 `/cost` 启动失败

→ 检查是否有遗留 PID：`lsof -nP -iTCP:8788 -sTCP:LISTEN`；若有，`kill <pid>`。
→ 检查是否有遗留 `.port` 文件：`cat ~/.claude/projects/cost-estimation/.port`，必要时手动删除。

## 计算阶段

### 反向模式提示 `BUDGET_NEGATIVE`

→ 输入的 `target_total - other_cost <= 0`。修正目标总造价或其他费用。

### Forward 模式三档结果差距太大

→ 多半是 PDR 三档跨度太大（电信行业 P10=2.4 vs P90=27.7）。如想收窄区间，进"参数管理 → 生产率"调 P10 / P90。

### Excel 下载 500 错误

→ 看 `/tmp/cost-estimation.log`。常见原因：
  - openpyxl 版本不兼容（升级 `openpyxl`）
  - 模板被删（重跑 `/cost-estimation:setup`）
  - `COST_DATA_DIR` 没有写权限（检查 exports 目录权限）

## 数据丢失

### "我误删了项目"

→ 项目软删除策略：检查 SQLite `projects.deleted_at` 字段。如已硬删，从 `~/.claude/projects/cost-estimation/db/cost.sqlite.bak` 恢复（如有备份）。

### "FP 编辑误改了"

→ FP 表有 5 版历史快照，前端"参数管理 → 快照"Tab 可回滚（v1 实现仅查看，回滚 API `POST /api/projects/{id}/functions/restore?version=N`）。

## 升级（v1.0 → v1.1）

> v1.1 引入 FK ondelete CASCADE，但 **SQLite 不支持在已存在的库上 ALTER FK 约束**。

如果你从 v1.0 升级且**仍遇到删除项目时 500 错误**，按以下步骤重建库：

```bash
DATA_DIR="$HOME/.claude/projects/cost-estimation"

# 1. 备份旧库
cp "$DATA_DIR/db/cost.sqlite" "$DATA_DIR/db/cost.sqlite.v1.0.bak"

# 2. 导出旧库（如需保留 SQL 全量备份）
sqlite3 "$DATA_DIR/db/cost.sqlite" .dump > /tmp/v1.0-data.sql

# 3. 删除旧库
rm "$DATA_DIR/db/cost.sqlite"

# 4. 用 v1.1 schema 重新初始化
PLUGIN_DIR="$HOME/.claude/plugins/cache/cost-estimation"
"$PLUGIN_DIR/server/.venv/bin/python" -m app.bootstrap \
  --db "$DATA_DIR/db/cost.sqlite" \
  --seed "$PLUGIN_DIR/server/app/data/csbmk_202510.json"

# 5. 手动重建项目元信息（建议）
```

> 建议：如果项目数较少，最简单的做法是删除旧库后从 v1.0 备份的 Excel 报告封面页誊抄项目元信息，再重新上传 FP 清单。

### 升级数据迁移注意

- 全局参数表（params_global）会从 seed JSON 重建为 v1.1 默认值
- 项目元信息（projects 表）需要手动重建（建议从 v1.0 备份的 Excel 报告封面页誊抄）
- FP 清单需重新上传或手动录入
- 历史快照（fp_snapshots）会丢失（v1.0 累积的版本历史）

## 卸载

```bash
/plugin uninstall cost-estimation
rm -rf ~/.claude/projects/cost-estimation
rm -rf ~/.claude/plugins/cache/cost-estimation
```

## 联系

issues: <repo-url>/issues
