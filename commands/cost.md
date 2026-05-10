---
description: 启动造价评估 Web 服务（生成随机 token，写入 .token / .port / .pid，浏览器打开）
allowed-tools: Bash
---

启动后端：

1. 定义路径：
   ```bash
   PLUGIN_DIR="$HOME/.claude/plugins/cache/cost-estimation"
   [ -d "$PLUGIN_DIR" ] || PLUGIN_DIR="$HOME/.claude/plugins/data/cost-estimation"
   DATA_DIR="$HOME/.claude/projects/cost-estimation"
   mkdir -p "$DATA_DIR"
   ```

2. 检测 8788 端口是否占用，若占用则尝试 8789–8800：
   ```bash
   PORT=""
   for p in 8788 8789 8790 8791 8792 8793 8794 8795 8796 8797 8798 8799 8800; do
     if ! lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then
       PORT=$p
       break
     fi
   done
   [ -z "$PORT" ] && { echo "✗ 8788–8800 端口全部占用"; exit 1; }
   echo "$PORT" > "$DATA_DIR/.port"
   ```

3. 生成一次性 token：
   ```bash
   TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
   echo "$TOKEN" > "$DATA_DIR/.token"
   chmod 600 "$DATA_DIR/.token"
   ```

4. 启动 uvicorn（后台），把 PID 写入 .pid：
   ```bash
   cd "$PLUGIN_DIR/server"
   AUTH_TOKEN="$TOKEN" \
   COST_DATABASE_URL="sqlite:///$DATA_DIR/db/cost.sqlite" \
   COST_WEB_DIST_DIR="$PLUGIN_DIR/web/dist" \
   COST_UPLOAD_DIR="$DATA_DIR/uploads" \
   COST_EXPORT_DIR="$DATA_DIR/exports" \
   nohup ".venv/bin/uvicorn" \
     app.main:app --host 127.0.0.1 --port "$PORT" \
     > /tmp/cost-estimation.log 2>&1 &
   echo $! > "$DATA_DIR/.pid"
   ```

5. 轮询 `http://127.0.0.1:$PORT/health` 直到就绪（最多 10 秒）：
   ```bash
   for i in $(seq 1 20); do
     if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
       break
     fi
     sleep 0.5
   done
   ```

6. 在默认浏览器打开（携带 token）：
   ```bash
   URL="http://127.0.0.1:$PORT/?t=$TOKEN"
   case "$(uname -s)" in
     Darwin) open "$URL" ;;
     Linux)  xdg-open "$URL" ;;
     MINGW*|MSYS*|CYGWIN*) start "$URL" ;;
     *) echo "请手动打开：$URL" ;;
   esac
   echo "✓ 已启动: $URL"
   echo "  日志: /tmp/cost-estimation.log"
   echo "  停止: 运行 /cost-estimation:cost-stop"
   ```
