---
description: 停止造价评估后端服务并清理 .pid / .token / .port
allowed-tools: Bash
---

1. 读取 PID 并 kill：
   ```bash
   DATA_DIR="$HOME/.claude/projects/cost-estimation"
   if [ -f "$DATA_DIR/.pid" ]; then
     PID=$(cat "$DATA_DIR/.pid")
     if kill -0 "$PID" 2>/dev/null; then
       kill "$PID" && echo "✓ 已停止 PID=$PID"
       sleep 1
       kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
     else
       echo "PID=$PID 已不存在"
     fi
     rm -f "$DATA_DIR/.pid"
   else
     echo "未找到 .pid，尝试用 lsof 兜底..."
     PORT_FILE="$DATA_DIR/.port"
     if [ -f "$PORT_FILE" ]; then
       PORT=$(cat "$PORT_FILE")
       LISTENERS=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)
       [ -n "$LISTENERS" ] && kill $LISTENERS && echo "✓ 已停止端口 $PORT 上的进程"
     fi
   fi
   ```

2. 清理一次性 token：
   ```bash
   rm -f "$DATA_DIR/.token" "$DATA_DIR/.port"
   echo "✓ 已清理 .token / .port"
   ```
