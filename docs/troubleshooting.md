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

## 卸载

```bash
/plugin uninstall cost-estimation
rm -rf ~/.claude/projects/cost-estimation
rm -rf ~/.claude/plugins/cache/cost-estimation
```

## 联系

issues: <repo-url>/issues
